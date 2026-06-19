"""
api/compare_routes.py — Parallel dual-text comparison endpoint.

POST /api/compare
    Runs the full analysis pipeline (C++ BPV micro-layer + spaCy macro-layer
    + dissonance engine) on two texts simultaneously using a thread pool, then
    returns both window sequences plus a computed delta summary.

    The C++ psycho_core.compare_texts() call processes both texts in parallel
    at the micro (BPV orthographic) level.  The spaCy macro pass and
    dissonance scoring are applied per-window in the Python layer, mirroring
    what _run_pipeline() does for single texts.

    The response shape is:
        {
          "text_a":  <full _run_pipeline() result for text A>,
          "text_b":  <full _run_pipeline() result for text B>,
          "delta":   <aggregate comparison metrics>
        }

    The frontend uses this response to:
      - Show dual window-pill navigation (A pills + B pills)
      - Render per-window details for A or B independently
      - Render the Unified Overlay with both datasets
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Reuse the already-validated single-document pipeline from routes.py.
# _run_pipeline() handles tokenisation, micro/macro analysis, dissonance
# scoring, and somatic engine — everything needed per window.
from api.routes import _run_pipeline

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    text_a: str = Field(..., min_length=1, description="First intercept text")
    text_b: str = Field(..., min_length=1, description="Second intercept text")
    language_code: str = Field("EN", description="Language for Text A: EN|ES|FR|JA")
    language_code_b: Optional[str] = Field(
        None,
        description="Language for Text B (defaults to language_code)"
    )
    document_id_a: Optional[str] = Field(None, description="Optional ID for text A")
    document_id_b: Optional[str] = Field(None, description="Optional ID for text B")
    window_size: int = Field(1000, ge=100, description="Characters per window")
    stride: int = Field(500, ge=50, description="Step size between windows")
    dissonance_threshold: float = Field(2.5, ge=0.5, description="Δ threshold")


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------

_MICRO_KEYS = ["intensity", "anxiety", "attention", "emotion", "agitation", "complexity"]


def _compute_delta(
    results_a: Dict[str, Any],
    results_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute aggregate delta metrics between two _run_pipeline() results.

    Returns:
        window_count_a / _b    — number of windows in each text
        aligned_pairs          — min(|A|, |B|) — windows compared index-by-index
        mean_micro_delta       — per-key mean absolute difference across paired windows
        dissonance_a / _b      — total dissonance events per text
        dissonance_delta       — B − A event count difference
        window_deltas          — per-paired-window micro vector differences
    """
    wins_a: List[Dict[str, Any]] = results_a.get("windows", [])
    wins_b: List[Dict[str, Any]] = results_b.get("windows", [])
    pairs = min(len(wins_a), len(wins_b))

    # Per-key mean absolute delta across aligned window pairs
    key_sum: Dict[str, float] = {k: 0.0 for k in _MICRO_KEYS}
    window_deltas: List[Dict[str, Any]] = []

    for i in range(pairs):
        va = wins_a[i]["micro"]["vectors"]
        vb = wins_b[i]["micro"]["vectors"]
        delta_row: Dict[str, float] = {}
        for k in _MICRO_KEYS:
            d = abs(va.get(k, 0.0) - vb.get(k, 0.0))
            key_sum[k] += d
            delta_row[k] = round(d, 4)
        window_deltas.append({
            "window_index": i,
            "micro_delta":  delta_row,
        })

    mean_micro_delta = {
        k: round(v / pairs, 4) if pairs else 0.0
        for k, v in key_sum.items()
    }

    total_dis_a = sum(len(w["dissonance_events"]) for w in wins_a)
    total_dis_b = sum(len(w["dissonance_events"]) for w in wins_b)

    return {
        "window_count_a":   len(wins_a),
        "window_count_b":   len(wins_b),
        "aligned_pairs":    pairs,
        "mean_micro_delta": mean_micro_delta,
        "dissonance_a":     total_dis_a,
        "dissonance_b":     total_dis_b,
        "dissonance_delta": total_dis_b - total_dis_a,
        "window_deltas":    window_deltas,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/compare")
def compare_texts(req: CompareRequest) -> Dict[str, Any]:
    """
    Run the full psycholinguistic pipeline on two texts in parallel and
    return both result sets plus a computed delta summary.

    The C++ compare_engine handles parallel BPV micro scoring; the Python
    layer adds spaCy macro scores, dissonance events, and somatic analysis.
    """
    if req.stride >= req.window_size:
        raise HTTPException(422, detail="stride must be strictly less than window_size")

    lang_a = req.language_code.upper()
    lang_b = (req.language_code_b or req.language_code).upper()

    doc_a = req.document_id_a or f"cmp_a_{uuid.uuid4().hex[:6]}"
    doc_b = req.document_id_b or f"cmp_b_{uuid.uuid4().hex[:6]}"

    try:
        # Run both full pipelines in parallel threads.
        # ThreadPoolExecutor releases the GIL for C++ work inside _run_pipeline.
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_a = pool.submit(
                _run_pipeline,
                req.text_a, lang_a,
                req.window_size, req.stride,
                req.dissonance_threshold, doc_a,
            )
            fut_b = pool.submit(
                _run_pipeline,
                req.text_b, lang_b,
                req.window_size, req.stride,
                req.dissonance_threshold, doc_b,
            )
            results_a = fut_a.result()
            results_b = fut_b.result()

    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc))

    delta = _compute_delta(results_a, results_b)

    return {
        "text_a": results_a,
        "text_b": results_b,
        "delta":  delta,
    }
