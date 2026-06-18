"""
MODULE 5 — Persistent Database Schema
Reads and writes the exact entity JSON structure defined in the spec.
Maintains target continuity across multiple documents.

Entity JSON structure:
    entity_id                        — unique target identifier
    identity                         — designator, aliases, operational profile
    processing_metrics               — document count, confidence score
    psycholinguistic_baselines       — per-variable μ, σ, EMA snapshots
    dissonance_ledger                — append-only list of dissonance events
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Schema template
# ---------------------------------------------------------------------------

def _empty_baseline_entry() -> Dict[str, float]:
    return {"mu_mean": 0.0, "sigma_variance": 0.0, "current_ema": 0.0}


def new_entity(
    primary_designator: str,
    known_aliases: Optional[List[str]] = None,
    suspected_agency: str = "Unknown",
    steganography_risk: str = "High",
) -> Dict[str, Any]:
    """
    Create a fresh entity record that matches the exact JSON schema from the spec.
    A unique entity_id is generated automatically.
    """
    return {
        "entity_id": f"tgt_{uuid.uuid4().hex[:7]}",
        "identity": {
            "primary_designator": primary_designator,
            "known_aliases": known_aliases or [],
            "operational_profile": {
                "suspected_agency": suspected_agency,
                "steganography_risk": steganography_risk,
            },
        },
        "processing_metrics": {
            "total_documents_analyzed": 0,
            "baseline_confidence_score": 0.0,
        },
        "psycholinguistic_baselines": {
            "micro_orthographic": {
                "A_attention": _empty_baseline_entry(),
                "S_anxiety":   _empty_baseline_entry(),
            },
            "macro_semantic": {
                "power_authority": _empty_baseline_entry(),
            },
        },
        "dissonance_ledger": [],
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_entity(path: str) -> Dict[str, Any]:
    """
    Load an entity from *path*.
    If the file does not exist, returns a default entity (does NOT write it).
    """
    if not os.path.exists(path):
        return new_entity(
            primary_designator="Target_Delta",
            known_aliases=["Author_X"],
        )
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_entity(entity: Dict[str, Any], path: str) -> None:
    """Atomically persist *entity* to *path* (write → rename)."""
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(entity, fh, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Entity mutation helpers
# ---------------------------------------------------------------------------

def increment_document_count(entity: Dict[str, Any]) -> None:
    entity["processing_metrics"]["total_documents_analyzed"] += 1


def update_confidence_score(entity: Dict[str, Any], score: float) -> None:
    entity["processing_metrics"]["baseline_confidence_score"] = round(score, 6)


def update_baselines(
    entity: Dict[str, Any],
    micro_snapshot: Dict[str, Dict],
    macro_snapshot: Dict[str, Dict],
) -> None:
    """
    Sync engine baseline snapshots back into the entity record.

    *micro_snapshot* and *macro_snapshot* are dicts of the form:
        { "variable_name": {"mu": float, "sigma": float, "ema": float, "n": int} }
    """
    pbl = entity["psycholinguistic_baselines"]

    for key, stats in micro_snapshot.items():
        if key not in pbl["micro_orthographic"]:
            pbl["micro_orthographic"][key] = _empty_baseline_entry()
        entry = pbl["micro_orthographic"][key]
        entry["mu_mean"]       = round(stats.get("mu", 0.0), 6)
        entry["sigma_variance"] = round(stats.get("sigma", 0.0), 6)
        entry["current_ema"]   = round(stats.get("ema", 0.0), 6)

    for key, stats in macro_snapshot.items():
        if key not in pbl["macro_semantic"]:
            pbl["macro_semantic"][key] = _empty_baseline_entry()
        entry = pbl["macro_semantic"][key]
        entry["mu_mean"]       = round(stats.get("mu", 0.0), 6)
        entry["sigma_variance"] = round(stats.get("sigma", 0.0), 6)
        entry["current_ema"]   = round(stats.get("ema", 0.0), 6)


def append_dissonance_events(
    entity: Dict[str, Any],
    events: List[Dict[str, Any]],
    document_id: str,
) -> None:
    """
    Append new dissonance events to the entity ledger.
    Each event dict must conform to the DissonanceEvent.to_dict() structure.
    """
    ledger = entity.setdefault("dissonance_ledger", [])
    for ev in events:
        ledger.append({
            "event_id":              ev.get("event_id", f"dis_{uuid.uuid4().hex[:6]}"),
            "timestamp":             ev.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "source_document_id":    document_id,
            "trigger_type":          ev.get("trigger_type", "Macro-Micro Conflict"),
            "vectors_involved":      ev.get("vectors_involved", []),
            "delta_score":           ev.get("delta_score", 0.0),
            "algorithmic_conclusion": ev.get("algorithmic_conclusion", ""),
        })


def compute_confidence_score(entity: Dict[str, Any]) -> float:
    """
    Heuristic confidence score:
        min(1.0, total_docs / 10) — grows toward 1.0 as more documents
        are processed, since baselines become more statistically reliable.
    """
    docs = entity["processing_metrics"]["total_documents_analyzed"]
    return min(1.0, docs / 10.0)
