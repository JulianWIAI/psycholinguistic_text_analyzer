"""
api/graph_routes.py
Graph Layer REST endpoints for the Corpus Explorer.

Endpoints:
  GET  /api/corpora                          — list all corpora
  POST /api/corpora/create                   — create a new corpus tag
  POST /api/graph/index_document             — index an analysis result into the graph
  POST /api/graph/query                      — query co-occurrences + spectral anomalies
  GET  /api/graph/document_correlations/{id} — intra-document device↔field correlations
"""
import os
from typing import Any, Dict, List, Optional

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
    literary: Optional[Dict[str, Any]] = None
    psychological_payload: Optional[Dict[str, Any]] = None
    macro_scores: Optional[Dict[str, Any]] = None
    somatic: Optional[Dict[str, Any]] = None


class GraphQueryRequest(BaseModel):
    corpus_ids: List[str]
    include_spectrum: bool = True


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

    Extracts stylistic devices, word fields, macro clusters, and somatic
    archetypes and wires them to the document node and its corpora.
    """
    # 1. Upsert the document node
    _graph.add_node(req.doc_id, "Document", {"language": req.language})

    # 2. Attach to corpora
    for corpus_id in req.corpus_ids:
        if not _graph.has_node(corpus_id):
            # Auto-create a minimal corpus node so the edge is valid
            _graph.add_node(corpus_id, "Corpus", {"name": corpus_id, "description": ""})
        _graph.add_edge(req.doc_id, corpus_id, "BELONGS_TO", weight=1.0)

    # 3. Stylistic devices from literary.rhetorical_findings
    if req.literary:
        rhetorical_findings = req.literary.get("rhetorical_findings", [])
        if isinstance(rhetorical_findings, list):
            for finding in rhetorical_findings:
                if not isinstance(finding, dict):
                    continue
                device_type = finding.get("device_type")
                if not device_type:
                    continue
                node_id = f"device_{device_type.lower()}"
                _graph.add_node(
                    node_id,
                    "StylisticDevice",
                    {"device": device_type},
                )
                _graph.add_edge(req.doc_id, node_id, "EXHIBITS_DEVICE", weight=1.0)

        # 4. Word fields from literary.word_fields.field_density
        word_fields = req.literary.get("word_fields", {})
        if isinstance(word_fields, dict):
            field_density = word_fields.get("field_density", {})
            if isinstance(field_density, dict):
                for field_name, density in field_density.items():
                    density_val = float(density) if density is not None else 0.0
                    if density_val <= 0:
                        continue
                    node_id = f"field_{field_name.lower()}"
                    _graph.add_node(
                        node_id,
                        "WordField",
                        {"field": field_name},
                    )
                    _graph.add_edge(req.doc_id, node_id, "CO_OCCURS_WITH", weight=density_val)

    # 5. Macro cluster scores
    # macro_scores is {cluster: {pole: score}} — sum pole magnitudes for combined weight
    if req.macro_scores and isinstance(req.macro_scores, dict):
        for cluster, score_data in req.macro_scores.items():
            combined_score = 0.0
            if isinstance(score_data, dict):
                combined_score = sum(
                    abs(float(v)) for v in score_data.values()
                    if isinstance(v, (int, float))
                )
            elif isinstance(score_data, (int, float)):
                combined_score = abs(float(score_data))

            if combined_score <= 0.05:
                continue

            node_id = f"cluster_{cluster.lower()}"
            _graph.add_node(
                node_id,
                "MacroCluster",
                {"cluster": cluster},
            )
            _graph.add_edge(req.doc_id, node_id, "CO_OCCURS_WITH", weight=combined_score)

    # 6. Somatic archetype (field is quersumme_archetype in somatic_engine.py)
    if req.somatic and isinstance(req.somatic, dict):
        archetype = req.somatic.get("quersumme_archetype") or req.somatic.get("archetype")
        if archetype:
            node_id = f"somatic_{archetype.lower().replace(' ', '_')}"
            _graph.add_node(
                node_id,
                "SomaticArchetype",
                {"archetype": archetype},
            )
            _graph.add_edge(req.doc_id, node_id, "HAS_SOMATIC_SIGNATURE", weight=1.0)

    # 7. Persist
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
