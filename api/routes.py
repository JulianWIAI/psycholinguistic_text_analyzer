"""
MODULE 6 — FastAPI Routes (Backend)
Exposes the full multi-language analysis pipeline as REST API endpoints.

All endpoints now accept an optional language_code parameter:
    "EN" (default) | "ES" | "FR" | "JA"

The LanguageRouter selects the correct micro + macro analyzers; the
dissonance engine always receives the standardized six-vector MicroResult
so Z-scores and baselines remain cross-language comparable.

Endpoints:
    POST   /api/analyze         — full pipeline on submitted text
    POST   /api/control         — seed baselines from a control text
    GET    /api/entity          — fetch current entity record
    POST   /api/entity          — create / overwrite entity record
    GET    /api/entity/ledger   — dissonance event ledger
    DELETE /api/entity/ledger   — clear ledger
    GET    /api/languages       — list supported language codes
    GET    /api/health          — liveness check
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import database.schema as db
from dissonance.engine import DissonanceEngine
from language.router import LanguageRouter, SUPPORTED_LANGUAGES
from tokenizer.rolling_window import RollingWindowTokenizer

router = APIRouter()

DB_PATH = "entity_db.json"

# ---------------------------------------------------------------------------
# Singletons — shared across requests for baseline continuity
# ---------------------------------------------------------------------------
_lang_router       = LanguageRouter()
_dissonance_engine = DissonanceEngine()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw text to analyze")
    language_code: str = Field("EN", description="ISO language code: EN, ES, FR, JA")
    document_id: Optional[str] = Field(None, description="Optional document identifier")
    window_size: int = Field(1000, ge=100, description="Characters per window")
    stride: int = Field(500, ge=50, description="Step size between windows")
    dissonance_threshold: float = Field(2.5, ge=0.5, description="Δ threshold for events")


class ControlTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Control / reference text")
    language_code: str = Field("EN", description="ISO language code: EN, ES, FR, JA")


class EntityCreateRequest(BaseModel):
    primary_designator: str
    known_aliases: List[str] = []
    suspected_agency: str = "Unknown"
    steganography_risk: str = "High"


# ---------------------------------------------------------------------------
# Core pipeline helper
# ---------------------------------------------------------------------------

def _flatten_macro(cluster_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Flatten {cluster: {pole: score}} → {"cluster_pole": score}."""
    return {
        f"{cluster}_{pole}": score
        for cluster, poles in cluster_scores.items()
        for pole, score in poles.items()
    }


def _run_pipeline(
    text: str,
    language_code: str,
    window_size: int,
    stride: int,
    threshold: float,
    document_id: str,
) -> Dict[str, Any]:
    """
    Execute the full analysis pipeline for one document.

    The LanguageRouter provides the correct micro/macro analyzers for
    the given language; the dissonance engine always receives standardized
    six-vector micro scores so baselines remain cross-language comparable.
    """
    tokenizer      = RollingWindowTokenizer(window_size=window_size, stride=stride)
    micro_analyzer = _lang_router.micro(language_code)
    macro_analyzer = _lang_router.macro(language_code)
    _dissonance_engine.threshold = threshold

    windows = tokenizer.tokenize(text)
    window_results: List[Dict[str, Any]] = []

    for win in windows:
        micro_result = micro_analyzer.analyze(win.text)
        macro_result = macro_analyzer.analyze(win.text)

        # Standardized six-vector micro dict (works for all languages)
        micro_vectors = micro_result.filled_vectors()

        # Flatten macro cluster scores
        flat_macro = _flatten_macro(macro_result.cluster_scores)

        dis = _dissonance_engine.analyze_window(
            micro_scores=micro_vectors,
            macro_scores=flat_macro,
            document_id=document_id,
        )

        window_results.append({
            "window_index":  win.index,
            "start_char":    win.start_char,
            "end_char":      win.end_char,
            "reset_reason":  win.reset_reason,
            "language":      language_code,
            "micro": {
                "vectors": {k: round(v, 4) for k, v in micro_vectors.items()},
                "raw":     micro_result.raw,
            },
            "macro": {
                "total_words":    macro_result.total_words,
                "cluster_scores": {
                    cluster: {pole: round(score, 6) for pole, score in poles.items()}
                    for cluster, poles in macro_result.cluster_scores.items()
                },
                "semantic_hits": len(macro_result.hits),
            },
            "z_scores_micro": {k: round(v, 4) for k, v in dis.z_scores_micro.items()},
            "z_scores_macro": {k: round(v, 4) for k, v in dis.z_scores_macro.items()},
            "ema_snapshot":   {k: round(v, 4) for k, v in dis.ema_snapshot.items()},
            "dissonance_events": [
                {
                    "event_id":   e.event_id,
                    "timestamp":  e.timestamp,
                    "trigger_type": e.trigger_type,
                    "vectors":    e.vectors_involved,
                    "delta":      e.delta_score,
                    "conclusion": e.algorithmic_conclusion,
                }
                for e in dis.dissonance_events
            ],
        })

    return {
        "document_id":   document_id,
        "language":      language_code,
        "total_windows": len(windows),
        "windows":       window_results,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze")
def analyze_text(req: AnalysisRequest) -> Dict[str, Any]:
    """Run the full psycholinguistic pipeline on submitted text."""
    if req.stride >= req.window_size:
        raise HTTPException(422, detail="stride must be strictly less than window_size")

    doc_id = req.document_id or f"doc_{uuid.uuid4().hex[:6]}"

    try:
        analysis = _run_pipeline(
            text=req.text,
            language_code=req.language_code.upper(),
            window_size=req.window_size,
            stride=req.stride,
            threshold=req.dissonance_threshold,
            document_id=doc_id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except RuntimeError as exc:
        # Raised by ModelRegistry when a spaCy model is missing
        raise HTTPException(503, detail=str(exc))

    # Persist to entity database
    entity = db.load_entity(DB_PATH)
    db.increment_document_count(entity)

    snapshot = _dissonance_engine.get_baseline_snapshot()
    db.update_baselines(entity, snapshot["micro"], snapshot["macro"])

    all_events = [ev for win in analysis["windows"] for ev in win["dissonance_events"]]
    db.append_dissonance_events(entity, all_events, doc_id)

    confidence = db.compute_confidence_score(entity)
    db.update_confidence_score(entity, confidence)
    db.save_entity(entity, DB_PATH)

    return analysis


@router.post("/control")
def seed_control_text(req: ControlTextRequest) -> Dict[str, Any]:
    """Seed engine baselines from a control / reference text."""
    try:
        micro_analyzer = _lang_router.micro(req.language_code.upper())
        macro_analyzer = _lang_router.macro(req.language_code.upper())
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc))

    tokenizer = RollingWindowTokenizer()
    windows   = tokenizer.tokenize(req.text)
    seeded    = 0

    for win in windows:
        micro  = micro_analyzer.analyze(win.text)
        macro  = macro_analyzer.analyze(win.text)
        _dissonance_engine.seed_baselines(
            micro_observations=micro.filled_vectors(),
            macro_observations=_flatten_macro(macro.cluster_scores),
        )
        seeded += 1

    snapshot = _dissonance_engine.get_baseline_snapshot()
    entity   = db.load_entity(DB_PATH)
    db.update_baselines(entity, snapshot["micro"], snapshot["macro"])
    db.save_entity(entity, DB_PATH)

    return {
        "status":            "baselines seeded",
        "language":          req.language_code.upper(),
        "windows_processed": seeded,
        "baseline_snapshot": snapshot,
    }


@router.get("/languages")
def list_languages() -> Dict[str, str]:
    """List all supported language codes and their names."""
    return SUPPORTED_LANGUAGES


@router.get("/entity")
def get_entity() -> Dict[str, Any]:
    return db.load_entity(DB_PATH)


@router.post("/entity")
def create_entity(req: EntityCreateRequest) -> Dict[str, Any]:
    entity = db.new_entity(
        primary_designator=req.primary_designator,
        known_aliases=req.known_aliases,
        suspected_agency=req.suspected_agency,
        steganography_risk=req.steganography_risk,
    )
    db.save_entity(entity, DB_PATH)
    return entity


@router.get("/entity/ledger")
def get_ledger() -> List[Dict[str, Any]]:
    return db.load_entity(DB_PATH).get("dissonance_ledger", [])


@router.delete("/entity/ledger")
def clear_ledger() -> Dict[str, str]:
    entity = db.load_entity(DB_PATH)
    entity["dissonance_ledger"] = []
    db.save_entity(entity, DB_PATH)
    return {"status": "ledger cleared"}


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status":         "ok",
        "engine":         "PsychoLinguistic Analysis Engine v2.0",
        "loaded_models":  __import__("language.registry", fromlist=["ModelRegistry"])
                          .ModelRegistry.loaded_models(),
        "languages":      list(SUPPORTED_LANGUAGES.keys()),
    }
