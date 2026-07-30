"""
vad_layer — NRC Valence-Arousal-Dominance Lexicon Analysis Package

Provides the analyze_vad() function for computing the psychological
emotional payload of an intercept text across three independent axes:
  - Valence    (Negative ↔ Positive)
  - Arousal    (Calm     ↔ Agitated)
  - Dominance  (Submissive ↔ In-control)

Lexicon files must be placed in vad_layer/lexicons/ as TSV files
named {lang_lower}_vad.tsv (e.g. en_vad.tsv, ru_vad.tsv).

Expected TSV column order:
    word <TAB> valence <TAB> arousal <TAB> dominance
A single optional header row is auto-detected and skipped.
"""

from .vad_analyzer import analyze_vad  # noqa: F401 — re-exported for convenience

__all__ = ["analyze_vad"]
