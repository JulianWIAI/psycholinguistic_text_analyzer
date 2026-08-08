"""
graph_layer/engine.py
Pure-Python in-memory graph engine. Mirrors the C++ GraphEngine API so
graph_layer/__init__.py can swap backends transparently.
"""
import json
import math
import os
import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False


class GraphEngine:
    """
    In-memory directed multigraph for corpus cross-reference analysis.

    Nodes are keyed by string ID and carry a type_str and property dict.
    Edges are stored in forward (_adj) and reverse (_radj) adjacency lists
    as (target, relation, weight) / (source, relation, weight) tuples.
    All public methods are thread-safe via a reentrant lock.
    """

    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._nodes: Dict[str, dict] = {}
        # forward adjacency:  source -> [(target, relation, weight), ...]
        self._adj: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)
        # reverse adjacency: target -> [(source, relation, weight), ...]
        self._radj: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)
        # corpus_id -> set of member document node IDs
        self._corpus_members: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------
    # Node / edge mutation
    # ------------------------------------------------------------------

    def add_node(self, id: str, type_str: str, properties: dict = {}) -> None:
        """Add or upsert a node. Thread-safe."""
        with self._lock:
            self._nodes[id] = {
                "type": type_str,
                "properties": dict(properties),
            }
            if type_str == "Corpus" and id not in self._corpus_members:
                self._corpus_members[id] = set()

    def add_edge(
        self,
        source: str,
        target: str,
        relation_str: str,
        weight: float = 1.0,
    ) -> None:
        """Append a directed edge. Thread-safe."""
        with self._lock:
            self._adj[source].append((target, relation_str, weight))
            self._radj[target].append((source, relation_str, weight))
            if relation_str == "BELONGS_TO":
                # source document belongs to target corpus
                if target not in self._corpus_members:
                    self._corpus_members[target] = set()
                self._corpus_members[target].add(source)

    # ------------------------------------------------------------------
    # Read-only queries
    # ------------------------------------------------------------------

    def has_node(self, id: str) -> bool:
        with self._lock:
            return id in self._nodes

    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    def edge_count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._adj.values())

    def list_corpora(self) -> List[dict]:
        """Return metadata dicts for all Corpus-type nodes."""
        with self._lock:
            return [
                {"id": nid, "properties": data["properties"]}
                for nid, data in self._nodes.items()
                if data["type"] == "Corpus"
            ]

    # ------------------------------------------------------------------
    # Co-occurrence matrix
    # ------------------------------------------------------------------

    _FEATURE_TYPES = {"StylisticDevice", "WordField", "MacroCluster", "AffectNode"}

    def get_co_occurrence_matrix(self, corpus_ids: List[str]) -> dict:
        """
        Build an n×n co-occurrence matrix over feature nodes shared across
        documents that belong to any of the given corpora.

        Returns
        -------
        dict with keys:
            nodes       — sorted list of feature-node IDs
            matrix      — list[list[float]] of shape n×n
            corpus_ids  — echo of input
        """
        with self._lock:
            # 1. Collect document node IDs for the requested corpora
            doc_ids: Set[str] = set()
            for cid in corpus_ids:
                doc_ids.update(self._corpus_members.get(cid, set()))

            # 2. Collect feature nodes reachable from those docs
            feature_nodes: Set[str] = set()
            for doc_id in doc_ids:
                for (tgt, _rel, _wt) in self._adj.get(doc_id, []):
                    if tgt in self._nodes and self._nodes[tgt]["type"] in self._FEATURE_TYPES:
                        feature_nodes.add(tgt)

            node_list = sorted(feature_nodes)
            n = len(node_list)
            node_idx = {nid: i for i, nid in enumerate(node_list)}

            matrix = [[0.0] * n for _ in range(n)]

            # 3. For each document, accumulate pairwise products
            for doc_id in doc_ids:
                # gather (feature_index, weight) pairs for this document
                doc_features: List[Tuple[int, float]] = []
                for (tgt, _rel, wt) in self._adj.get(doc_id, []):
                    if tgt in node_idx:
                        doc_features.append((node_idx[tgt], wt))

                for (i, wi) in doc_features:
                    for (j, wj) in doc_features:
                        matrix[i][j] += wi * wj

            return {
                "nodes": node_list,
                "matrix": matrix,
                "corpus_ids": corpus_ids,
            }

    # ------------------------------------------------------------------
    # Laplacian
    # ------------------------------------------------------------------

    def compute_laplacian(self, corpus_ids: List[str]) -> dict:
        """
        Compute the graph Laplacian L = D − A from the co-occurrence matrix.

        The co-occurrence matrix is symmetrised before computing the Laplacian.
        Returns dict with keys: nodes, data (list[list[float]]).
        """
        co = self.get_co_occurrence_matrix(corpus_ids)
        nodes = co["nodes"]
        n = len(nodes)

        if n == 0:
            return {"nodes": [], "data": []}

        if _NUMPY_AVAILABLE:
            A = np.array(co["matrix"], dtype=float)
            A = (A + A.T) / 2.0
            D = np.diag(A.sum(axis=1))
            L = D - A
            return {"nodes": nodes, "data": L.tolist()}
        else:
            # Pure-Python fallback
            mat = co["matrix"]
            # symmetrise
            A = [[( mat[i][j] + mat[j][i]) / 2.0 for j in range(n)] for i in range(n)]
            D = [[A[i][j] if i == j else 0.0 for j in range(n)] for i in range(n)]
            # recompute diagonal from row sums
            for i in range(n):
                D[i][i] = sum(A[i])
            L = [[D[i][j] - A[i][j] for j in range(n)] for i in range(n)]
            return {"nodes": nodes, "data": L}

    # ------------------------------------------------------------------
    # Spectral analysis
    # ------------------------------------------------------------------

    def compute_laplacian_spectrum(self, corpus_ids: List[str]) -> dict:
        """
        Compute eigendecomposition of the Laplacian.

        Returns
        -------
        dict with keys:
            nodes         — feature node IDs
            eigenvalues   — up to 10 smallest eigenvalues (list[float])
            eigenvectors  — corresponding row-vectors (list[list[float]])
            fiedler_value — second smallest eigenvalue or None
        """
        lap = self.compute_laplacian(corpus_ids)
        nodes = lap["nodes"]
        n = len(nodes)

        if n == 0:
            return {
                "nodes": [],
                "eigenvalues": [],
                "eigenvectors": [],
                "fiedler_value": None,
            }

        if _NUMPY_AVAILABLE:
            L = np.array(lap["data"], dtype=float)
            eigenvalues, eigenvectors = np.linalg.eigh(L)
            k = min(10, n)
            return {
                "nodes": nodes,
                "eigenvalues": eigenvalues[:k].tolist(),
                "eigenvectors": eigenvectors[:, :k].T.tolist(),
                "fiedler_value": float(eigenvalues[1]) if n > 1 else None,
            }
        else:
            # numpy unavailable — return zero-filled spectrum
            k = min(10, n)
            return {
                "nodes": nodes,
                "eigenvalues": [0.0] * k,
                "eigenvectors": [[0.0] * n for _ in range(k)],
                "fiedler_value": None,
            }

    # ------------------------------------------------------------------
    # BFS traversal
    # ------------------------------------------------------------------

    def query_traversal(self, start_id: str, max_depth: int = 3) -> dict:
        """
        BFS from start_id up to max_depth hops over forward adjacency.

        Returns
        -------
        dict with keys:
            nodes — list of node dicts (id + type + properties)
            edges — list of edge dicts (source, target, relation, weight)
        """
        with self._lock:
            if start_id not in self._nodes:
                return {"nodes": [], "edges": []}

            visited_nodes: Dict[str, dict] = {}
            visited_edges: List[dict] = []
            # queue entries: (node_id, depth)
            queue: List[Tuple[str, int]] = [(start_id, 0)]
            seen: Set[str] = {start_id}

            while queue:
                current, depth = queue.pop(0)
                node_data = self._nodes[current]
                visited_nodes[current] = {
                    "id": current,
                    "type": node_data["type"],
                    "properties": node_data["properties"],
                }

                if depth >= max_depth:
                    continue

                for (tgt, rel, wt) in self._adj.get(current, []):
                    visited_edges.append({
                        "source": current,
                        "target": tgt,
                        "relation": rel,
                        "weight": wt,
                    })
                    if tgt not in seen:
                        seen.add(tgt)
                        queue.append((tgt, depth + 1))

            return {
                "nodes": list(visited_nodes.values()),
                "edges": visited_edges,
            }

    # ------------------------------------------------------------------
    # Document / corpus management
    # ------------------------------------------------------------------

    def list_corpus_documents(self, corpus_id: str) -> List[dict]:
        """
        Return a list of document-metadata dicts for every document that
        belongs to *corpus_id*.  Each dict contains:
            doc_id, title, language, is_legacy
        """
        with self._lock:
            doc_ids = self._corpus_members.get(corpus_id, set())
            result: List[dict] = []
            for doc_id in sorted(doc_ids):
                if doc_id not in self._nodes:
                    continue
                props = self._nodes[doc_id]["properties"]
                result.append({
                    "doc_id":    doc_id,
                    "title":     props.get("title"),
                    "language":  props.get("language"),
                    "is_legacy": props.get("is_legacy", False),
                })
            return result

    def get_document_matrix(self, doc_id: str) -> dict:
        """
        Build the co-occurrence matrix for a *single* document's feature nodes.

        Returns dict with keys: nodes, matrix.
        """
        with self._lock:
            if doc_id not in self._nodes:
                return {"nodes": [], "matrix": []}

            doc_features: List[Tuple[int, float]] = []
            feature_ids: List[str] = []
            seen: Set[str] = set()

            for (tgt, _rel, wt) in self._adj.get(doc_id, []):
                if tgt in self._nodes and self._nodes[tgt]["type"] in self._FEATURE_TYPES:
                    if tgt not in seen:
                        seen.add(tgt)
                        feature_ids.append(tgt)

            node_list = sorted(feature_ids)
            n = len(node_list)
            node_idx = {nid: i for i, nid in enumerate(node_list)}

            matrix = [[0.0] * n for _ in range(n)]

            for (tgt, _rel, wt) in self._adj.get(doc_id, []):
                if tgt in node_idx:
                    doc_features.append((node_idx[tgt], wt))

            for (i, wi) in doc_features:
                for (j, wj) in doc_features:
                    matrix[i][j] += wi * wj

            return {"nodes": node_list, "matrix": matrix}

    def update_node_property(self, node_id: str, key: str, value) -> bool:
        """Set a single property on an existing node.  Returns False if node not found."""
        with self._lock:
            if node_id not in self._nodes:
                return False
            self._nodes[node_id]["properties"][key] = value
            return True

    def remove_node(self, node_id: str) -> bool:
        """
        Remove *node_id* and every edge that touches it.
        Also removes the node from all corpus membership sets.
        Returns False if the node does not exist.
        """
        with self._lock:
            if node_id not in self._nodes:
                return False

            # Remove from every corpus membership set
            for members in self._corpus_members.values():
                members.discard(node_id)
            if node_id in self._corpus_members:
                del self._corpus_members[node_id]

            # Clean reverse adjacency of all targets this node points to
            for (tgt, _rel, _wt) in self._adj.get(node_id, []):
                if tgt in self._radj:
                    self._radj[tgt] = [
                        (s, r, w) for (s, r, w) in self._radj[tgt] if s != node_id
                    ]

            # Clean forward adjacency of all sources that point to this node
            for (src, _rel, _wt) in self._radj.get(node_id, []):
                if src in self._adj:
                    self._adj[src] = [
                        (t, r, w) for (t, r, w) in self._adj[src] if t != node_id
                    ]

            self._adj.pop(node_id, None)
            self._radj.pop(node_id, None)
            del self._nodes[node_id]
            return True

    def remove_corpus(self, corpus_id: str) -> bool:
        """
        Remove a corpus node and all its BELONGS_TO edges.
        Document nodes are kept; only their membership links to this corpus
        are removed.
        Returns False if the corpus node does not exist.
        """
        with self._lock:
            if corpus_id not in self._nodes:
                return False

            # Remove BELONGS_TO edges from each member document
            for (src, _rel, _wt) in self._radj.get(corpus_id, []):
                if src in self._adj:
                    self._adj[src] = [
                        (t, r, w) for (t, r, w) in self._adj[src]
                        if not (t == corpus_id and r == "BELONGS_TO")
                    ]

            self._radj.pop(corpus_id, None)
            self._adj.pop(corpus_id, None)
            self._corpus_members.pop(corpus_id, None)
            del self._nodes[corpus_id]
            return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_graph(self, filepath: str) -> None:
        """
        Serialize the graph to JSON and write atomically.
        Writes to <filepath>.tmp then replaces the target file.
        """
        with self._lock:
            payload: dict = {
                "nodes": self._nodes,
                "adjacency": [
                    [src, tgt, rel, wt]
                    for src, edges in self._adj.items()
                    for (tgt, rel, wt) in edges
                ],
                "corpus_members": {
                    k: list(v) for k, v in self._corpus_members.items()
                },
            }

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        tmp_path = filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)

    def load_graph(self, filepath: str) -> None:
        """
        Deserialize a previously saved graph from JSON.
        No-op if the file does not exist.
        """
        if not os.path.exists(filepath):
            return

        with open(filepath, "r", encoding="utf-8") as fh:
            payload = json.load(fh)

        with self._lock:
            self._nodes = payload.get("nodes", {})

            self._adj = defaultdict(list)
            self._radj = defaultdict(list)
            for entry in payload.get("adjacency", []):
                src, tgt, rel, wt = entry
                self._adj[src].append((tgt, rel, float(wt)))
                self._radj[tgt].append((src, rel, float(wt)))

            self._corpus_members = {
                k: set(v)
                for k, v in payload.get("corpus_members", {}).items()
            }
