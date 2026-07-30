"""
pds_layer/affect_loader.py
═══════════════════════════════════════════════════════════════════
NRC Affect Intensity Lexicon — Multilingual Loader & Cache Layer
═══════════════════════════════════════════════════════════════════

Public API
──────────
  load_affect_pack(lang)           → AffectPack
      PRIMARY entry point.  Load and cache the full 8-axis affect
      intensity pack for one language from the combined 4-column file.
      One lru_cache slot per language — maximally efficient.

  load_affect_lexicon(affect, lang) → Dict[str, float]
      COMPATIBILITY shim.  Delegates to load_affect_pack and slices
      out a single emotion axis.  Preserves the per-affect API used
      by any code written before Session 6.

Responsibility split
────────────────────
  Path resolution  →  affect_path_resolver.resolve_combined_affect_path()
  File parsing     →  affect_parser.parse_combined_affect_file()
  Caching          →  THIS module (@lru_cache on load_affect_pack)

This module owns no parsing or path logic — it is purely the
cache + orchestration layer that binds the two specialist modules
together and exposes a simple call interface to pds_analyzer.py.

Caching strategy
────────────────
The cache key for load_affect_pack is (lang,) — the entire 8-axis
pack for a language occupies one cache slot.  This replaces the old
(affect, lang) scheme, reducing cache entries from 8 × n_langs to
1 × n_langs and eliminating 7 redundant file reads per language.

  load_affect_pack("RU")  → reads intensity_ru.txt once, caches all 8 axes
  load_affect_pack("RU")  → cache hit, instant return

maxsize=16 accommodates 10 pipeline languages × 1.6× headroom.

Graceful degradation
────────────────────
At every failure point the function returns empty_affect_pack() —
a dict with all 8 emotion keys present but empty — rather than
raising.  Callers treat a missing word as score 0.0 and always
receive a structurally complete response.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict

from pds_layer.affect_parser       import (
    parse_combined_affect_file,
    empty_affect_pack,
    AffectPack,
)
from pds_layer.affect_path_resolver import resolve_combined_affect_path


# ---------------------------------------------------------------------------
# Primary public API — load a full 8-axis language pack
# ---------------------------------------------------------------------------

@lru_cache(maxsize=16)   # one slot per language; 10 langs × 1.6× headroom
def load_affect_pack(lang: str) -> AffectPack:
    """
    Load and cache the full 8-axis NRC Affect Intensity pack for *lang*.

    Reads a single combined 4-column file (intensity_{lang}.txt) and
    returns a nested dict mapping every recognised emotion label to its
    word→score dictionary for the requested language.

    Parameters
    ----------
    lang : str
        ISO-style language code, case-insensitive (EN, DE, RU, ZH,
        AR, FA, KO, ES, FR, JA).  Unknown codes fall back to the
        English base file via the resolver.

    Returns
    -------
    AffectPack  — Dict[str, Dict[str, float]]
        {
            "anger":        {"word": score, ...},
            "fear":         {"word": score, ...},
            "anticipation": {"word": score, ...},
            "trust":        {"word": score, ...},
            "surprise":     {"word": score, ...},
            "sadness":      {"word": score, ...},
            "joy":          {"word": score, ...},
            "disgust":      {"word": score, ...},
        }
        All 8 keys are always present.  Empty dicts mean the lexicon
        file was not installed or contained no valid rows for that axis.

    Notes
    -----
    • The lru_cache key is the normalised lang string.  Normalisation
      (strip + upper) is applied BEFORE caching so "ru", " RU ", "Ru"
      all resolve to the same cache slot after the first call.
    • Thread-safe under Python's GIL — concurrent first-calls for the
      same language will not produce duplicate file reads.
    """
    # ── Normalise the lang code before it becomes part of the cache key ───
    # lru_cache hashes the raw argument; normalising here rather than at
    # the call site means every variant hits the same slot.
    lang_norm: str = lang.strip().upper()

    # ── Resolve the best-available combined file path ──────────────────────
    # Returns a confirmed-existing absolute path, or None.
    filepath = resolve_combined_affect_path(lang_norm)

    if filepath is None:
        # No combined file found for this language (or EN fallback).
        # Return a structurally complete but empty pack so the caller
        # always receives a valid AffectPack without needing to guard.
        return empty_affect_pack()

    # ── Parse the file and return the fully populated pack ────────────────
    # File handle is opened here (I/O layer) and the pure parser receives
    # it — keeping the parser free of any filesystem concerns.
    try:
        with open(filepath, encoding="utf-8") as fh:
            return parse_combined_affect_file(fh, lang_norm)
    except OSError:
        # Covers permissions errors, network mount timeouts, TOCTOU races
        # (file existed at resolver check, gone by open time), etc.
        # Return empty pack rather than propagating the exception.
        return empty_affect_pack()


# ---------------------------------------------------------------------------
# Compatibility shim — single-axis accessor (Sessions 4 / 5 API)
# ---------------------------------------------------------------------------

def load_affect_lexicon(affect: str, lang: str = "EN") -> Dict[str, float]:
    """
    Return the word→score dict for a single emotion axis in *lang*.

    This function preserves the API introduced in Sessions 4/5 so that
    any existing call site that requests one axis at a time continues to
    work without modification.  Internally it simply loads the full
    language pack (one cache hit) and slices out the requested axis.

    Parameters
    ----------
    affect : str
        Canonical affect label, case-insensitive
        (anger, fear, anticipation, trust, surprise, sadness, joy, disgust).
    lang : str
        ISO-style language code.  Defaults to "EN".

    Returns
    -------
    Dict[str, float]
        word → intensity score in [0.0, 1.0].
        Returns {} for unknown affect labels or uninstalled lexicons.

    Performance note
    ────────────────
    The first call for a given lang triggers one file read; every
    subsequent call (regardless of affect) is a pure dict lookup in
    the already-cached AffectPack.  Calling this function 8 times for
    the same language is therefore equivalent to calling load_affect_pack
    once — no redundant I/O occurs.
    """
    affect_norm: str = affect.strip().lower()
    lang_norm:   str = lang.strip().upper()

    # Retrieve the full pack (cache hit after the first call per language).
    pack: AffectPack = load_affect_pack(lang_norm)

    # Return the requested axis, or {} for unknown labels.
    return pack.get(affect_norm, {})
