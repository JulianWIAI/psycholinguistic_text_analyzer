"""
api/graph_routes.py
Graph Layer REST endpoints for the Corpus Explorer.

Endpoints:
  GET    /api/corpora                             — list all corpora
  POST   /api/corpora/create                      — create a new corpus tag
  DELETE /api/corpora/{corpus_id}                 — remove a corpus node
  POST   /api/graph/index_document                — index an analysis result into the graph
  POST   /api/graph/query                         — query co-occurrences + spectral anomalies
  GET    /api/graph/corpus_documents/{corpus_id}  — list documents in a corpus
  GET    /api/graph/matrix/document/{doc_id}      — isolated feature matrix for one document
  POST   /api/graph/matrix/divergence             — divergence D = T̃ − C̃ between two matrices
  GET    /api/graph/document/{doc_id}             — get document node metadata
  PUT    /api/graph/document/{doc_id}             — rename a document node
  DELETE /api/graph/document/{doc_id}             — remove a document node
  GET    /api/graph/document_correlations/{id}    — intra-document device↔field correlations
"""
import math
import os
from typing import Any, Dict, List, Optional

from graph_layer.feature_extractor import (
    extract_literary_features,
    extract_macro_features,
    extract_somatic_features,
    extract_affect_features,
)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import graph_layer
from graph_layer import GraphEngine

router = APIRouter()

_GRAPH_PATH = "database/graph.json"
_graph = GraphEngine()
if os.path.exists(_GRAPH_PATH):
    try:
        _graph.load_graph(_GRAPH_PATH)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class CorpusCreateRequest(BaseModel):
    name: str
    description: str = ""


class IndexDocumentRequest(BaseModel):
    doc_id: str
    corpus_ids: List[str]
    language: str = "EN"
    title: Optional[str] = None
    literary: Optional[Dict[str, Any]] = None
    psychological_payload: Optional[Dict[str, Any]] = None
    macro_scores: Optional[Dict[str, Any]] = None
    somatic: Optional[Dict[str, Any]] = None
    windows: Optional[List[Dict[str, Any]]] = None  # all windows (reserved for multi-window indexing)


class GraphQueryRequest(BaseModel):
    corpus_ids: List[str]
    include_spectrum: bool = True


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None


class DivergenceRequest(BaseModel):
    ephemeral_matrix: Dict[str, Any]   # {nodes: list[str], matrix: list[list[float]]}
    corpus_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/corpora")
def list_corpora() -> dict:
    """Return all registered corpus nodes and the active backend."""
    return {
        "corpora": _graph.list_corpora(),
        "backend": graph_layer._BACKEND,
    }


@router.post("/corpora/create")
def create_corpus(req: CorpusCreateRequest) -> dict:
    """
    Register a new corpus tag node.
    Returns 409 if a corpus with the derived ID already exists.
    """
    corpus_id = f"corpus_{req.name.lower().replace(' ', '_')}"

    if _graph.has_node(corpus_id):
        raise HTTPException(
            status_code=409,
            detail=f"Corpus '{corpus_id}' already exists.",
        )

    _graph.add_node(corpus_id, "Corpus", {"name": req.name, "description": req.description})
    _graph.save_graph(_GRAPH_PATH)

    return {"id": corpus_id, "name": req.name, "created": True}


@router.post("/graph/index_document")
def index_document(req: IndexDocumentRequest) -> dict:
    """
    Index an analysis result into the graph.

    Extracts stylistic devices, word fields, macro clusters, somatic
    archetypes, and PDS/VAD affect feelings and wires them to the
    document node and its corpora.
    """
    # 1. Upsert the document node (store title if provided)
    doc_props: Dict[str, Any] = {"language": req.language}
    if req.title:
        doc_props["title"] = req.title.strip()
    _graph.add_node(req.doc_id, "Document", doc_props)

    # 2. Attach to corpora
    for corpus_id in req.corpus_ids:
        if not _graph.has_node(corpus_id):
            _graph.add_node(corpus_id, "Corpus", {"name": corpus_id, "description": ""})
        _graph.add_edge(req.doc_id, corpus_id, "BELONGS_TO", weight=1.0)

    # 3–4. Stylistic devices + word fields (via shared extractor)
    for feat in extract_literary_features(req.literary):
        _graph.add_node(feat.node_id, feat.node_type, feat.props)
        relation = "EXHIBITS_DEVICE" if feat.node_type == "StylisticDevice" else "CO_OCCURS_WITH"
        _graph.add_edge(req.doc_id, feat.node_id, relation, weight=feat.weight)

    # 5. Macro cluster scores (via shared extractor)
    for feat in extract_macro_features(req.macro_scores):
        _graph.add_node(feat.node_id, feat.node_type, feat.props)
        _graph.add_edge(req.doc_id, feat.node_id, "CO_OCCURS_WITH", weight=feat.weight)

    # 6. Somatic archetype (via shared extractor)
    for feat in extract_somatic_features(req.somatic):
        _graph.add_node(feat.node_id, feat.node_type, feat.props)
        _graph.add_edge(req.doc_id, feat.node_id, "HAS_SOMATIC_SIGNATURE", weight=feat.weight)

    # 7. PDS / VAD affect feelings — each significant emotion dimension becomes
    #    an AffectNode so feelings co-occur with word fields in the corpus matrix.
    for feat in extract_affect_features(req.psychological_payload):
        _graph.add_node(feat.node_id, feat.node_type, feat.props)
        _graph.add_edge(req.doc_id, feat.node_id, "HAS_AFFECT", weight=feat.weight)

    # 8. Persist
    _graph.save_graph(_GRAPH_PATH)

    return {
        "indexed": True,
        "doc_id": req.doc_id,
        "nodes": _graph.node_count(),
        "edges": _graph.edge_count(),
    }


@router.post("/graph/query")
def query_graph(req: GraphQueryRequest) -> dict:
    """
    Return co-occurrence matrix and optional Laplacian spectrum
    for the requested corpora.
    """
    if not req.corpus_ids:
        raise HTTPException(
            status_code=400,
            detail="corpus_ids must not be empty.",
        )

    co = _graph.get_co_occurrence_matrix(req.corpus_ids)

    if req.include_spectrum and len(co["nodes"]) >= 2:
        spectrum = _graph.compute_laplacian_spectrum(req.corpus_ids)
    else:
        spectrum = {
            "eigenvalues": [],
            "eigenvectors": [],
            "fiedler_value": None,
        }

    return {
        "co_occurrence": co,
        "spectrum": spectrum,
        "corpus_ids": req.corpus_ids,
    }


@router.delete("/corpora/{corpus_id}")
def delete_corpus(corpus_id: str) -> dict:
    """Remove a corpus node and all its membership edges (documents are kept)."""
    removed = _graph.remove_corpus(corpus_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Corpus '{corpus_id}' not found.")
    _graph.save_graph(_GRAPH_PATH)
    return {"deleted": True, "corpus_id": corpus_id}


@router.get("/graph/corpus_documents/{corpus_id}")
def list_corpus_documents(corpus_id: str) -> dict:
    """Return all documents that belong to the given corpus."""
    if not _graph.has_node(corpus_id):
        raise HTTPException(status_code=404, detail=f"Corpus '{corpus_id}' not found.")
    docs = _graph.list_corpus_documents(corpus_id)
    return {"corpus_id": corpus_id, "documents": docs}


@router.get("/graph/matrix/document/{doc_id}")
def document_matrix(doc_id: str) -> dict:
    """Return the isolated feature co-occurrence matrix for a single document."""
    if not _graph.has_node(doc_id):
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    result = _graph.get_document_matrix(doc_id)
    return result


@router.post("/graph/matrix/divergence")
def matrix_divergence(req: DivergenceRequest) -> dict:
    """
    Compute the structural divergence D = T̃ − C̃ between an ephemeral matrix T
    and the stored corpus baseline C.

    Both matrices are Jaccard-normalised before subtraction.
    Returns: nodes, diff_matrix, frobenius_norm, t_node_count, c_node_count.
    """
    t_nodes: List[str] = req.ephemeral_matrix.get("nodes", [])
    t_raw:   List[List[float]] = req.ephemeral_matrix.get("matrix", [])

    if not t_nodes or not t_raw:
        raise HTTPException(status_code=400, detail="ephemeral_matrix must contain nodes and matrix.")

    corpus_co = _graph.get_co_occurrence_matrix([req.corpus_id])
    c_nodes: List[str] = corpus_co["nodes"]
    c_raw:   List[List[float]] = corpus_co["matrix"]

    # Union of all feature nodes, sorted for a stable ordering
    union_nodes = sorted(set(t_nodes) | set(c_nodes))
    n = len(union_nodes)

    if n == 0:
        return {
            "nodes": [], "diff_matrix": [], "frobenius_norm": 0.0,
            "t_node_count": 0, "c_node_count": 0,
        }

    t_idx = {nid: i for i, nid in enumerate(t_nodes)}
    c_idx = {nid: i for i, nid in enumerate(c_nodes)}

    def _align(raw: List[List[float]], idx: Dict[str, int]) -> List[List[float]]:
        """Embed *raw* (indexed by *idx*) into the union node space."""
        m = [[0.0] * n for _ in range(n)]
        for ui, un in enumerate(union_nodes):
            if un not in idx:
                continue
            si = idx[un]
            for uj, um in enumerate(union_nodes):
                if um not in idx:
                    continue
                sj = idx[um]
                m[ui][uj] = raw[si][sj]
        return m

    def _jaccard(m: List[List[float]]) -> List[List[float]]:
        """Jaccard-normalise: v[i][j] = 2·M[i][j] / (M[i][i] + M[j][j])."""
        jac = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                denom = m[i][i] + m[j][j]
                jac[i][j] = 2.0 * m[i][j] / denom if denom > 0 else 0.0
        return jac

    T_aligned = _align(t_raw, t_idx)
    C_aligned = _align(c_raw, c_idx)

    T_jac = _jaccard(T_aligned)
    C_jac = _jaccard(C_aligned)

    D = [[T_jac[i][j] - C_jac[i][j] for j in range(n)] for i in range(n)]

    frob = math.sqrt(sum(D[i][j] ** 2 for i in range(n) for j in range(n)))

    return {
        "nodes":          union_nodes,
        "diff_matrix":    D,
        "frobenius_norm": round(frob, 6),
        "t_node_count":   len(t_nodes),
        "c_node_count":   len(c_nodes),
    }


@router.get("/graph/document/{doc_id}")
def get_document(doc_id: str) -> dict:
    """Return metadata for a single document node."""
    if not _graph.has_node(doc_id):
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    # Access internal state via public API — return properties
    result = _graph.query_traversal(doc_id, max_depth=0)
    nodes = result.get("nodes", [])
    if not nodes:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return nodes[0]


@router.put("/graph/document/{doc_id}")
def update_document(doc_id: str, req: DocumentUpdateRequest) -> dict:
    """Update metadata on a document node (currently: title)."""
    if not _graph.has_node(doc_id):
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    if req.title is not None:
        _graph.update_node_property(doc_id, "title", req.title.strip())
    _graph.save_graph(_GRAPH_PATH)
    return {"updated": True, "doc_id": doc_id}


@router.delete("/graph/document/{doc_id}")
def delete_document(doc_id: str) -> dict:
    """Remove a document node and all its edges from the graph."""
    removed = _graph.remove_node(doc_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    _graph.save_graph(_GRAPH_PATH)
    return {"deleted": True, "doc_id": doc_id}


@router.get("/graph/document_correlations/{doc_id}")
def document_correlations(doc_id: str) -> dict:
    """
    BFS traversal from a document node (depth 2) to expose intra-document
    feature correlations grouped by relation type.
    """
    result = _graph.query_traversal(doc_id, max_depth=2)

    # Group edges by relation type for convenience
    by_relation: Dict[str, list] = {}
    for edge in result["edges"]:
        rel = edge["relation"]
        by_relation.setdefault(rel, []).append(edge)

    # feature_count excludes the doc node itself
    doc_in_nodes = any(n["id"] == doc_id for n in result["nodes"])
    feature_count = len(result["nodes"]) - (1 if doc_in_nodes else 0)

    return {
        "doc_id": doc_id,
        "traversal": result,
        "correlations_by_relation": by_relation,
        "feature_count": feature_count,
    }
