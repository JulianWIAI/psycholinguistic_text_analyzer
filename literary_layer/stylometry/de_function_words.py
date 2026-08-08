"""
Literary Layer — German Function Word List (Phase 8)
Top German function words for Burrows' Delta stylometric fingerprinting.
All words are in their most common surface form (not lemmatised) since
frequency-of-form — not frequency-of-lemma — is what Burrows' Delta measures.
"""
from __future__ import annotations
from typing import List

FUNCTION_WORDS: List[str] = [
    "die", "der", "und", "in", "den", "von", "zu", "das", "mit",
    "sich", "des", "auf", "für", "ist", "im", "dem", "nicht",
    "ein", "eine", "als", "auch", "es", "an", "werden", "aus",
    "er", "hat", "dass", "sie", "nach", "wird", "bei", "einer",
    "um", "am", "sind", "noch", "wie", "einem", "über", "einen",
    "so", "zum", "war", "haben", "nur", "oder", "aber", "vor",
    "zur", "bis", "mehr", "durch", "man", "sein", "wurde", "ihr",
    "hatte", "kann", "gegen", "vom", "können", "schon", "wenn",
    "habe", "seine", "mark", "ihre", "dann", "unter", "wir",
    "mir", "ihn", "diese", "diesem", "dieses", "worden",
]
