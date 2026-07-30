"""
pds_layer/affect_path_resolver.py
═══════════════════════════════════════════════════════════════════
Multilingual Affect Intensity Lexicon — Path Resolver
═══════════════════════════════════════════════════════════════════

Single-responsibility module: resolve filesystem paths for NRC Affect
Intensity lexicon files.  This module performs NO file I/O beyond
os.path.isfile() existence checks — all caching and parsing is handled
by affect_loader.py and affect_parser.py respectively.

Two resolution strategies are supported side-by-side:

  Combined format (primary — Session 6)
  ──────────────────────────────────────
  One file per language holds ALL 8 emotion dimensions in 4-column
  TAB-separated format:
      English Word | Emotion | Score | Translated Word

  File naming:   intensity_{lang_lower}.txt
  Examples:      intensity_ru.txt, intensity_ar.txt, intensity_en.txt

  Resolution function: resolve_combined_affect_path(lang)
    Tier 1 — language-specific combined file:  intensity_ru.txt
    Tier 2 — English combined base:            intensity_en.txt

  Per-affect format (legacy — Sessions 4/5)
  ──────────────────────────────────────────
  One file per (affect, language) pair:
      intensity_anger_ru.txt, intensity_anger.txt, …

  Resolution function: resolve_affect_path(affect, lang)   [unchanged]
    Tier 1 — language-specific:  intensity_anger_ru.txt
    Tier 2 — English base:       intensity_anger.txt

Return contract (both functions)
─────────────────────────────────
• Returns an absolute path string confirmed to exist on disk.
• Returns None if no file is found at any tier.
  → caller must return an empty/zeroed structure; never raises.

Supported language codes
────────────────────────
  EN  DE  RU  ZH  AR  FA  KO  ES  FR  JA

Unknown codes fall back silently to English in both resolvers.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Path to the shared lexicon directory
# ---------------------------------------------------------------------------

# Absolute path to this file's directory:  <project_root>/pds_layer/
_THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))

# Sibling lexicon directory used by all language layers:
#   <project_root>/vad_layer/lexicons/
_LEXICON_DIR: str = os.path.normpath(
    os.path.join(_THIS_DIR, "..", "vad_layer", "lexicons")
)

# ---------------------------------------------------------------------------
# Language code → filename suffix mapping
# ---------------------------------------------------------------------------
# Each entry maps the canonical uppercase ISO-style language code (as used
# throughout the rest of the pipeline) to the lowercase suffix that appears
# in the intensity filename:
#
#   "RU" → "_ru"   →  intensity_anger_ru.txt
#   "EN" → ""      →  intensity_anger.txt      (English is the base file)
#
# Languages absent from this dict are treated identically to "EN" —
# the resolver skips Tier 1 and goes straight to the English base file.
# This makes the dict safe to extend incrementally as new translated
# intensity lexicons are acquired.

_LANG_SUFFIX: Dict[str, str] = {
    "EN": "",      # English is the base — no suffix appended
    "DE": "_de",   # German
    "RU": "_ru",   # Russian
    "ZH": "_zh",   # Mandarin Chinese
    "AR": "_ar",   # Arabic
    "FA": "_fa",   # Farsi / Persian
    "KO": "_ko",   # Korean
    "ES": "_es",   # Spanish
    "FR": "_fr",   # French
    "JA": "_ja",   # Japanese
}

# ---------------------------------------------------------------------------
# Affect label → base filename stem mapping
# ---------------------------------------------------------------------------
# Maps each canonical affect label to the invariant part of its filename
# (before any language suffix).  The stem is lowercase and matches the
# actual file naming convention used by the NRC Affect Intensity Lexicon.
#
# This dict is the single source of truth for which affects are recognised
# by the engine.  Adding a 9th axis requires one new entry here only.

_AFFECT_STEM: Dict[str, str] = {
    "anger":        "intensity_anger",
    "fear":         "intensity_fear",
    "anticipation": "intensity_anticipation",
    "trust":        "intensity_trust",
    "surprise":     "intensity_surprise",
    "sadness":      "intensity_sadness",
    "joy":          "intensity_joy",
    "disgust":      "intensity_disgust",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_affect_path(affect: str, lang: str) -> Optional[str]:
    """
    Return the absolute path of the best-available intensity file for
    the given *affect* + *lang* pair, using a two-tier fallback strategy.

    Resolution order
    ────────────────
    Tier 1 — Language-specific file (skipped for EN and unknown langs):
        <lexicon_dir>/intensity_<affect>_<lang_suffix>.txt
        e.g. intensity_anger_ru.txt

    Tier 2 — English base file (always attempted as final fallback):
        <lexicon_dir>/intensity_<affect>.txt
        e.g. intensity_anger.txt

    Parameters
    ----------
    affect : str
        Canonical affect label, case-insensitive.
        Must be a key in _AFFECT_STEM; returns None for unknown labels.
    lang : str
        ISO-style language code as used by the rest of the pipeline
        (EN, DE, RU, ZH, AR, FA, KO, ES, FR, JA).  Unknown codes fall
        back silently to English without logging or raising.

    Returns
    -------
    str | None
        Absolute filesystem path of the chosen lexicon file, guaranteed
        to exist at the moment of the call.  None if no file was found
        at either tier — the caller must return {} in that case.

    Notes
    -----
    • This function is a pure path resolver — it calls os.path.isfile()
      but never opens, reads, or writes files.
    • It is intentionally NOT cached here; caching at this layer would
      mask newly installed language files until the process restarts.
      The caller (affect_loader.load_affect_lexicon) already pins the
      *parsed* dict via lru_cache, so the isfile() overhead is incurred
      at most once per (affect, lang) pair per process.
    """
    # ── Normalise inputs ──────────────────────────────────────────────────
    affect_key: str = affect.strip().lower()
    lang_key:   str = lang.strip().upper()

    # Unknown affect label — nothing to resolve.
    stem: Optional[str] = _AFFECT_STEM.get(affect_key)
    if stem is None:
        return None

    # Get the suffix for this language (empty string for EN or unknown).
    suffix: str = _LANG_SUFFIX.get(lang_key, "")

    # ── Tier 1: language-specific file ───────────────────────────────────
    # Skipped when suffix is "" (English or unrecognised language) because
    # that would produce the same candidate as Tier 2 — a redundant check.
    if suffix:
        lang_path: str = os.path.join(_LEXICON_DIR, f"{stem}{suffix}.txt")
        if os.path.isfile(lang_path):
            return lang_path
        # File not present — fall through to Tier 2 silently.
        # Do NOT log here; missing language files are expected during
        # incremental deployment (e.g. only Russian anger is translated
        # so far) and logging every miss would flood production logs.

    # ── Tier 2: English base file ─────────────────────────────────────────
    # This is the universal fallback.  If even the English base is absent
    # the lexicon was never installed — return None so the caller can
    # score all words at 0.0 rather than raising an exception.
    base_path: str = os.path.join(_LEXICON_DIR, f"{stem}.txt")
    if os.path.isfile(base_path):
        return base_path

    # Neither tier resolved to an existing file.
    return None


def list_available_langs(affect: str) -> list:
    """
    Diagnostic helper: return the list of language codes for which a
    per-affect intensity file currently exists in the lexicon directory.

    Useful during deployment to audit which (affect, lang) combinations
    are installed without having to list the directory manually.

    Parameters
    ----------
    affect : str
        Canonical affect label (case-insensitive).

    Returns
    -------
    list[str]
        Sorted list of ISO language codes with a physical file present,
        e.g. ['AR', 'EN', 'RU'].  Empty if the affect is unknown.
    """
    affect_key: str = affect.strip().lower()
    stem: Optional[str] = _AFFECT_STEM.get(affect_key)
    if stem is None:
        return []

    found: list = []
    for lang_code, suffix in _LANG_SUFFIX.items():
        filename = f"{stem}{suffix}.txt"
        if os.path.isfile(os.path.join(_LEXICON_DIR, filename)):
            found.append(lang_code)

    return sorted(found)


# ---------------------------------------------------------------------------
# Combined-format resolver  (Session 6 — one file per language, 8 emotions)
# ---------------------------------------------------------------------------

def resolve_combined_affect_path(lang: str) -> Optional[str]:
    """
    Return the absolute path of the best-available *combined* affect
    intensity file for *lang*.

    The combined format stores all 8 emotion dimensions in a single
    4-column TSV file per language:

        intensity_en.txt   — English
        intensity_ru.txt   — Russian
        intensity_ar.txt   — Arabic
        …

    Resolution order
    ────────────────
    Tier 1 — language-specific combined file:
        <lexicon_dir>/intensity_<lang_lower>.txt
        e.g. intensity_ru.txt  for lang="RU"

    Tier 2 — English combined base file:
        <lexicon_dir>/intensity_en.txt
        Attempted whenever Tier 1 is skipped (EN input) or absent.

    Parameters
    ----------
    lang : str
        ISO-style language code, case-insensitive.
        Unknown codes that are not in _LANG_SUFFIX also reach Tier 2.

    Returns
    -------
    str | None
        Absolute filesystem path confirmed to exist, or None if neither
        tier finds a file.  The caller (affect_loader.load_affect_pack)
        must return empty_affect_pack() in the None case.

    Notes
    -----
    • Pure path resolver — calls os.path.isfile() but never opens files.
    • Not cached here; the caller caches the parsed AffectPack instead,
      so a freshly dropped intensity_ru.txt is picked up on next restart
      without any cache-busting logic.
    """
    lang_norm:  str = lang.strip().upper()
    lang_lower: str = lang_norm.lower()

    # ── Tier 1: language-specific combined file ───────────────────────────
    # Skipped for English because lang_lower would be "en" — the same path
    # Tier 2 tries, making it a redundant check rather than a separate tier.
    if lang_norm != "EN":
        lang_path: str = os.path.join(_LEXICON_DIR, f"intensity_{lang_lower}.txt")
        if os.path.isfile(lang_path):
            return lang_path
        # File absent — fall through to English base silently.

    # ── Tier 2: English combined base file ───────────────────────────────
    # Universal fallback.  If absent, the combined lexicon was never
    # installed for any language — return None and let caller score 0.0.
    en_path: str = os.path.join(_LEXICON_DIR, "intensity_en.txt")
    if os.path.isfile(en_path):
        return en_path

    return None


def list_combined_available_langs() -> list:
    """
    Diagnostic helper: return the list of language codes for which a
    combined intensity file (intensity_{lang}.txt) currently exists.

    Does not require an affect label — the combined file covers all 8
    dimensions simultaneously.

    Returns
    -------
    list[str]
        Sorted list of ISO language codes, e.g. ['AR', 'EN', 'RU'].
    """
    found: list = []
    for lang_code in _LANG_SUFFIX:
        lang_lower = lang_code.lower()
        filename   = f"intensity_{lang_lower}.txt"
        if os.path.isfile(os.path.join(_LEXICON_DIR, filename)):
            found.append(lang_code)
    return sorted(found)
