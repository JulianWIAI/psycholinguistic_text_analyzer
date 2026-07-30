"""
vad_layer/vad_analyzer.py
═══════════════════════════════════════════════════════════════════
NRC Valence-Arousal-Dominance (VAD) Lexicon Analysis Module
═══════════════════════════════════════════════════════════════════

Loads the correct NRC-VAD language dictionary, tokenizes the input
text through the project-wide spaCy model registry, and computes
aggregate emotional payload metrics.

Supported languages: EN, DE, RU, ZH, AR, FA, KO
(ES / FR / JA use EN-equivalent spaCy lemmatization paths and require
their own translated lexicon files to be present.)

Lexicon convention
------------------
Files must live at:  vad_layer/lexicons/nrc_vad_{lang_lower}.txt
Column order (English, 4-col):      word | valence | arousal | dominance
Column order (multilingual, 5-col): English Word | valence | arousal | dominance | Translated Word
All scores are expected to be in the [0.0, 1.0] range (NRC default).
An optional single header row is auto-detected via non-numeric 2nd cell.
For non-English languages the translated word (col 5) is used as the lookup
key so that spaCy lemmas in the target language match lexicon entries.

Algorithm
---------
1. Load (and LRU-cache) the language lexicon from disk.
2. Acquire the spaCy model via the project-wide ModelRegistry.
3. Iterate over every spaCy token; skip punctuation, whitespace,
   numbers, spaCy stop-words, and a supplemental generic-stop list.
4. For each remaining token, look up the *lemma* in the lexicon;
   fall back to the lowercased surface form if the lemma misses.
5. Accumulate (V, A, D) triples for all matched words.
6. Compute population mean (μ) and population standard deviation (σ)
   for each of the three axes.

Returns
-------
A dict suitable for direct JSON serialization:
{
  "valence_mean":    float,   # μ across matched words
  "valence_sigma":   float,   # σ (volatility) across matched words
  "arousal_mean":    float,
  "arousal_sigma":   float,
  "dominance_mean":  float,
  "dominance_sigma": float,
  "matched_count":   int,     # tokens that hit the lexicon
  "total_tokens":    int,     # all non-stop content tokens examined
  "words":           list,    # [{word, v, a, d}, …] — feeds the scatter plot
  "language":        str,
  "error":           str|None,
}
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Lexicon path resolution
# ---------------------------------------------------------------------------

# Absolute path to the lexicons sub-directory (sibling of this file).
_LEX_DIR: str = os.path.join(os.path.dirname(__file__), "lexicons")

# Maps each supported language code to its filename stem.
# Add new languages here and drop nrc_vad_{lang_lower}.txt into lexicons/.
_LANG_TO_STEM: Dict[str, str] = {
    "EN": "nrc_vad_en",
    "DE": "nrc_vad_de",
    "ES": "nrc_vad_es",
    "FR": "nrc_vad_fr",
    "RU": "nrc_vad_ru",
    "ZH": "nrc_vad_zh",
    "AR": "nrc_vad_ar",
    "FA": "nrc_vad_fa",
    "KO": "nrc_vad_ko",
    "JA": "nrc_vad_ja",
}

# Maps language codes to the spaCy model used by the existing macro-layer,
# so we share the already-cached model and never double-load anything.
_LANG_TO_MODEL: Dict[str, str] = {
    "EN": "en_core_web_sm",
    "DE": "de_core_news_sm",
    "ES": "es_core_news_sm",
    "FR": "fr_core_news_sm",
    "JA": "ja_core_news_sm",
    "RU": "ru_core_news_sm",
    "AR": "xx_ent_wiki_sm",
    "FA": "xx_ent_wiki_sm",
    "KO": "ko_core_news_sm",
    "ZH": "zh_core_web_sm",
}

# Fallback model used when the primary model isn't installed.
# en_core_web_sm is always installed as a project baseline.
_FALLBACK_MODEL: str = "en_core_web_sm"


# ---------------------------------------------------------------------------
# Lexicon loader (cached — each language TSV is read once per process)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=len(_LANG_TO_STEM))
def _load_lexicon(lang: str) -> Dict[str, Tuple[float, float, float]]:
    """
    Parse and cache the NRC-VAD TSV for *lang*.

    Returns
    -------
    dict mapping lowercase word → (valence, arousal, dominance)

    Raises
    ------
    ValueError       — if *lang* has no registered lexicon stem.
    FileNotFoundError — if the TSV file is absent from lexicons/.
    """
    stem = _LANG_TO_STEM.get(lang)
    if stem is None:
        raise ValueError(
            f"No VAD lexicon registered for language code '{lang}'. "
            f"Supported codes: {list(_LANG_TO_STEM.keys())}"
        )

    path = os.path.join(_LEX_DIR, f"{stem}.txt")
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"NRC-VAD lexicon not found at: '{path}'.  "
            "Download the NRC Valence-Arousal-Dominance Lexicon (and translated "
            "variants) from https://saifmohammad.com/WebPages/nrc-vad.html and "
            f"place the file as '{stem}.txt' inside vad_layer/lexicons/."
        )

    # For non-English languages the 5th column (index 4) holds the translated
    # word, which is the form spaCy lemmatizes to in the target language.
    # English files are 4-column (no translated word) and always use col 0.
    is_english: bool = (lang == "EN")

    lexicon: Dict[str, Tuple[float, float, float]] = {}
    with open(path, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh):
            line = raw_line.rstrip("\n")
            parts = line.split("\t")
            if len(parts) < 4:
                continue  # skip blank or malformed rows

            v_col, a_col, d_col = parts[1], parts[2], parts[3]

            # Auto-detect and skip a header row (non-numeric second column).
            if line_no == 0 and not _is_float(v_col):
                continue

            # Choose the right word key:
            #   English  → col 0 (the word itself, no translation column)
            #   Others   → col 4 (translated word); fall back to col 0 if empty
            if is_english or len(parts) < 5 or not parts[4].strip():
                word_key = parts[0].strip().lower()
            else:
                word_key = parts[4].strip().lower()

            if not word_key:
                continue

            try:
                lexicon[word_key] = (
                    float(v_col),
                    float(a_col),
                    float(d_col),
                )
            except ValueError:
                # Malformed numeric field — skip silently.
                continue

    return lexicon


def _is_float(s: str) -> bool:
    """Return True if *s* can be parsed as a float."""
    try:
        float(s)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# spaCy model access (via project-wide ModelRegistry)
# ---------------------------------------------------------------------------

def _get_nlp(lang: str):
    """
    Retrieve the spaCy model for *lang* via the project-wide ModelRegistry.

    Tries the primary model for the language; if that isn't installed,
    gracefully falls back to the multilingual *xx_ent_wiki_sm* model.
    Lemmatization quality degrades for the fallback, but the pipeline
    remains operational.
    """
    from language.registry import ModelRegistry

    primary = _LANG_TO_MODEL.get(lang, _FALLBACK_MODEL)
    try:
        return ModelRegistry.load(primary)
    except (RuntimeError, OSError):
        # Primary model not installed — fall back to the polyglot model.
        return ModelRegistry.load(_FALLBACK_MODEL)


# ---------------------------------------------------------------------------
# Supplemental stop-word list
# ---------------------------------------------------------------------------

# These high-frequency tokens carry no emotional signal.  They supplement
# spaCy's built-in is_stop flag, which can miss them in short or noisy text.
_GENERIC_STOPS: frozenset = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "to", "of", "in", "on", "at", "by",
    "for", "with", "this", "that", "these", "those", "it", "its", "not",
    "no", "nor", "so", "yet", "but", "and", "or", "if", "as", "up",
    "from", "into", "than", "then", "when", "what", "which", "who",
    "all", "any", "each", "few", "more", "most", "other", "some", "such",
    "also", "just", "very", "can", "i", "we", "he", "she", "they", "you",
})


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _mean(xs: List[float]) -> float:
    """Arithmetic mean of a non-empty list."""
    return sum(xs) / len(xs)


def _population_std(xs: List[float], mu: Optional[float] = None) -> float:
    """
    Population standard deviation (σ) of *xs*.
    Returns 0.0 for lists shorter than 2 to avoid misleading precision.
    """
    if len(xs) < 2:
        return 0.0
    mu = mu if mu is not None else _mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_vad(text: str, lang: str) -> Dict[str, Any]:
    """
    Analyse the emotional payload of *text* using the NRC-VAD lexicon
    for the target *lang*.

    Parameters
    ----------
    text : str
        Raw intercept text (any length; very short texts yield low coverage).
    lang : str
        ISO-style language code: "EN", "DE", "RU", "ZH", "AR", "FA", "KO",
        "ES", "FR", or "JA".

    Returns
    -------
    dict — see module docstring for full field list.
    """
    # Canonical uppercase code for all downstream lookups.
    lang = lang.strip().upper()

    # Neutral-midpoint fallback returned on error.
    _EMPTY: Dict[str, Any] = {
        "valence_mean":    0.5,
        "valence_sigma":   0.0,
        "arousal_mean":    0.5,
        "arousal_sigma":   0.0,
        "dominance_mean":  0.5,
        "dominance_sigma": 0.0,
        "matched_count":   0,
        "total_tokens":    0,
        "words":           [],
        "language":        lang,
        "error":           None,
    }

    # ── 1. Load lexicon ───────────────────────────────────────────────────
    try:
        lexicon = _load_lexicon(lang)
    except (ValueError, FileNotFoundError) as exc:
        return {**_EMPTY, "error": str(exc)}

    if not lexicon:
        return {**_EMPTY, "error": f"VAD lexicon for '{lang}' loaded but is empty."}

    # ── 2. Acquire spaCy model ────────────────────────────────────────────
    try:
        nlp = _get_nlp(lang)
    except Exception as exc:  # noqa: BLE001
        return {**_EMPTY, "error": f"spaCy model load failed: {exc}"}

    # ── 3. Tokenize via spaCy ─────────────────────────────────────────────
    doc = nlp(text)

    v_vals: List[float] = []
    a_vals: List[float] = []
    d_vals: List[float] = []
    words: List[Dict[str, Any]] = []
    total_tokens: int = 0

    for token in doc:
        # Skip structural tokens that carry no emotional weight.
        if token.is_punct or token.is_space or token.like_num:
            continue
        # Skip stop-words (spaCy's list + our supplement).
        if token.is_stop or token.lower_ in _GENERIC_STOPS:
            continue

        total_tokens += 1
        lemma = token.lemma_.lower().strip()

        # ── 4. Lexicon lookup ─────────────────────────────────────────────
        # Try lemma first; surface form as fallback (handles inflections the
        # lemmatizer might not resolve for lower-resource models).
        scores = lexicon.get(lemma) or lexicon.get(token.lower_)
        if scores is None:
            continue

        v, a, d = scores
        v_vals.append(v)
        a_vals.append(a)
        d_vals.append(d)
        words.append({
            "word": token.text,
            "v":    round(v, 4),
            "a":    round(a, 4),
            "d":    round(d, 4),
        })

    # ── 5. Return neutral midpoint if no matches ──────────────────────────
    if not v_vals:
        return {
            **_EMPTY,
            "total_tokens": total_tokens,
            "error": (
                "No lexicon matches found. The text may be too short, "
                "dominated by stop-words, or the lexicon coverage for this "
                f"language ('{lang}') may be insufficient."
            ),
        }

    # ── 6. Aggregate statistics ───────────────────────────────────────────
    v_mu = _mean(v_vals)
    a_mu = _mean(a_vals)
    d_mu = _mean(d_vals)

    return {
        "valence_mean":    round(v_mu, 4),
        "valence_sigma":   round(_population_std(v_vals, v_mu), 4),
        "arousal_mean":    round(a_mu, 4),
        "arousal_sigma":   round(_population_std(a_vals, a_mu), 4),
        "dominance_mean":  round(d_mu, 4),
        "dominance_sigma": round(_population_std(d_vals, d_mu), 4),
        "matched_count":   len(v_vals),
        "total_tokens":    total_tokens,
        "words":           words,
        "language":        lang,
        "error":           None,
    }
