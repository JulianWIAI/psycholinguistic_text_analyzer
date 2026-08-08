"""
graph_layer/ephemeral_matrix.py
--------------------------------
Build an in-memory co-occurrence matrix from a single /api/analyze pass.

The ephemeral matrix mirrors what GraphEngine stores in the persistent graph
but is computed on-the-fly from window_results so the local N×N matrix panel
can render without requiring an explicit index-to-graph step.

Feature types extracted per window
-----------------------------------
  device_*   literary.rhetorical_findings[*].device_type   weight = 1.0
  field_*    literary.word_fields.field_density[field]      weight = density value
  cluster_*  macro.cluster_scores[cluster]                  weight = sum |pole scores|
"""

from typing import Any, Dict, List, Tuple

from graph_layer.feature_extractor import (
    extract_literary_features,
    extract_macro_features,
    extract_affect_features,
)


def build_ephemeral_matrix(window_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate feature co-occurrences across all windows of one analysis run.

    Parameters
    ----------
    window_results : list of window dicts from _run_pipeline()

    Returns
    -------
    dict
        nodes  — sorted list of feature node IDs
        matrix — N×N list[list[float]] of raw co-occurrence sums
    """
    # First pass: collect all unique feature IDs and per-window feature vectors
    feature_set: Dict[str, None] = {}          # ordered set (insertion order preserved)
    window_feature_pairs: List[List[Tuple[str, float]]] = []

    for win in window_results:
        feats: List[Tuple[str, float]] = []

        # ── Literary: devices + word fields (shared extractor) ───────────────
        for rec in extract_literary_features(win.get("literary")):
            feature_set[rec.node_id] = None
            feats.append((rec.node_id, rec.weight))

        # ── Macro cluster scores (shared extractor) ──────────────────────────
        cluster_scores = (win.get("macro") or {}).get("cluster_scores")
        for rec in extract_macro_features(cluster_scores):
            feature_set[rec.node_id] = None
            feats.append((rec.node_id, rec.weight))

        # ── PDS / VAD affect feelings (shared extractor) ─────────────────────
        for rec in extract_affect_features(win.get("psychological_payload")):
            feature_set[rec.node_id] = None
            feats.append((rec.node_id, rec.weight))

        window_feature_pairs.append(feats)

    node_list = sorted(feature_set.keys())
    n = len(node_list)

    if n == 0:
        return {"nodes": [], "matrix": []}

    node_idx = {nid: i for i, nid in enumerate(node_list)}
    matrix = [[0.0] * n for _ in range(n)]

    # Second pass: accumulate pairwise outer products across all windows
    for feats in window_feature_pairs:
        resolved = [
            (node_idx[nid], wt)
            for (nid, wt) in feats
            if nid in node_idx
        ]
        for (i, wi) in resolved:
            for (j, wj) in resolved:
                matrix[i][j] += wi * wj

    return {"nodes": node_list, "matrix": matrix}
