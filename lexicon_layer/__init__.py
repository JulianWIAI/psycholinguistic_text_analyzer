"""
lexicon_layer — Unified NRC Lexicon Ingestion Package

Provides a single, language-agnostic ingestion engine capable of loading
both NRC lexicon formats used by the PsychoLinguistic Analysis Engine:

  4-column combined intensity format
      English Word | Emotion | Score | Translated Word
      → IntensityLexicon:  {word: {emotion: score}}

  5-column VAD format  (+ legacy 4-column EN-only variant)
      English Word | Valence | Arousal | Dominance | Translated Word
      → VADLexicon:  {word: {"v": float, "a": float, "d": float}}

Module layout
─────────────
  token_cleanser.py           — Stateless 3-gate token validation class
  lexicon_ingestion_engine.py — LexiconIngestionEngine: path resolution,
                                 parsing, instance-level caching, EN fallback

Public interface
────────────────
  from lexicon_layer import LexiconIngestionEngine, TokenCleanser

  engine = LexiconIngestionEngine()                    # uses vad_layer/lexicons/
  intensity = engine.load_intensity_lexicon("RU")      # IntensityLexicon
  vad       = engine.load_ousiometric_lexicon("AR")    # VADLexicon
"""

from .token_cleanser import TokenCleanser                              # noqa: F401
from .lexicon_ingestion_engine import (                                # noqa: F401
    LexiconIngestionEngine,
    # Type aliases — exported so callers can annotate without importing the
    # implementation module directly.
    EmotionProfile,
    VADScores,
    IntensityLexicon,
    VADLexicon,
)

__all__ = [
    # Core classes
    "LexiconIngestionEngine",
    "TokenCleanser",
    # Type aliases
    "EmotionProfile",
    "VADScores",
    "IntensityLexicon",
    "VADLexicon",
]
