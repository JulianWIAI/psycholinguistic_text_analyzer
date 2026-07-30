"""
pds_layer/affect_parser.py
═══════════════════════════════════════════════════════════════════
NRC Affect Intensity — Combined 4-Column File Parser
═══════════════════════════════════════════════════════════════════

Single-responsibility module: parse a combined NRC Affect Intensity
file that contains all 8 emotion dimensions for one language into an
in-memory nested dictionary.  This module performs NO path resolution,
NO caching, and NO file I/O beyond reading the file handle passed to
it — those concerns live in affect_path_resolver.py and affect_loader.py
respectively.

Expected file format
────────────────────
TAB-separated, one entry per line, exactly 4 columns:

    Column 1: English Word          — canonical NRC lemma (always present)
    Column 2: Emotion               — one of the 8 recognised dimension labels
    Column 3: Emotion-Intensity-Score — float in [0, 1]
    Column 4: Translated Word       — target-language lemma (may be empty for EN)

Example rows (Russian file):
    abandon  fear      0.375  покинуть
    abandon  sadness   0.625  покинуть
    abhor    anger     0.906  ненавидеть
    ...

Lines with fewer than 3 columns, a non-numeric score, or an unrecognised
emotion label are skipped silently — malformed rows never raise.

Word key selection
──────────────────
The parser determines which string to use as the dictionary key (the
lemma that will be looked up at query time) as follows:

  • Non-English languages:
      Use Column 4 (Translated Word) if it is non-empty after stripping.
      Fall back to Column 1 (English Word) if Column 4 is absent or blank.

  • English (lang == "EN"):
      Column 4 may be empty, identical to Column 1, or absent entirely.
      Always use Column 1 (English Word) directly — no Column 4 check.

  Both branches then apply .strip().lower() so lookups are
  case-insensitive and whitespace-tolerant.

Duplicate key handling
──────────────────────
Because multiple English words can share the same translation (e.g.
"anger" and "rage" both → "злость"), the parser keeps the HIGHEST
score seen for each (emotion, translated_word) pair.  This ensures
the most extreme intensity is preserved when two source lemmas
collapse onto the same target lemma.

Output schema
─────────────
{
    "anger":        { "word": score, ... },
    "fear":         { "word": score, ... },
    "anticipation": { "word": score, ... },
    "trust":        { "word": score, ... },
    "surprise":     { "word": score, ... },
    "sadness":      { "word": score, ... },
    "joy":          { "word": score, ... },
    "disgust":      { "word": score, ... },
}

All missing axes are present as empty dicts — the caller never needs
to guard against KeyError on the 8 canonical labels.
"""

from __future__ import annotations

from typing import Dict, IO

# ---------------------------------------------------------------------------
# Recognised emotion dimension labels
# ---------------------------------------------------------------------------
# These are the exact lowercase strings that appear in Column 2 of the
# NRC Affect Intensity Lexicon.  Any row with a different Column 2 value
# is silently skipped — this makes the parser safe against future columns
# or annotation artefacts without requiring a code change.

EMOTION_LABELS: frozenset = frozenset({
    "anger",
    "fear",
    "anticipation",
    "trust",
    "surprise",
    "sadness",
    "joy",
    "disgust",
})

# Convenience tuple in the canonical ordering used throughout the pipeline.
# Importing modules that need an ordered sequence should use this rather
# than reconstructing it.
EMOTION_LABELS_ORDERED: tuple = (
    "anger", "fear", "anticipation", "trust",
    "surprise", "sadness", "joy", "disgust",
)


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

# The nested dict returned by parse_combined_affect_file:
#   outer key = emotion label  (one of the 8 in EMOTION_LABELS)
#   inner key = word/lemma     (lowercase target-language string)
#   value     = intensity score clamped to [0.0, 1.0]
AffectPack = Dict[str, Dict[str, float]]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_combined_affect_file(fh: IO[str], lang: str) -> AffectPack:
    """
    Parse an open file handle to a combined NRC Affect Intensity file.

    Accepts a file handle rather than a path so the function remains
    pure and fully testable without touching the filesystem:

        with open(path, encoding="utf-8") as fh:
            pack = parse_combined_affect_file(fh, "RU")

    Parameters
    ----------
    fh : IO[str]
        Open text file handle positioned at the start of the file.
        The function reads to EOF; the caller is responsible for
        opening and closing the handle.
    lang : str
        ISO-style language code of the file being parsed, e.g. "RU".
        Case-insensitive; used solely to decide whether to prefer
        Column 4 (translated word) or Column 1 (English word) as the
        dictionary key.

    Returns
    -------
    AffectPack
        Nested dict ``{emotion_label: {word: score}}``.
        All 8 canonical emotion keys are always present — missing axes
        are empty dicts, never missing keys.  Scores are clamped to
        [0.0, 1.0].

    Raises
    ------
    Nothing.  All row-level errors are swallowed silently so a single
    malformed line can never abort a multi-thousand-line file parse.
    """
    # Normalise the language code once so per-row checks are O(1).
    is_english: bool = lang.strip().upper() == "EN"

    # Initialise the result pack with an empty dict for every recognised
    # emotion so callers can always subscript result["anger"] without
    # a KeyError, even for languages with zero lexicon coverage.
    result: AffectPack = {label: {} for label in EMOTION_LABELS}

    for raw_line in fh:
        # ── Strip and skip blank lines ────────────────────────────────────
        line: str = raw_line.strip()
        if not line:
            continue

        # ── Split on TAB ──────────────────────────────────────────────────
        # We need at least 3 columns (English word, emotion, score).
        # Column 4 (translated word) is optional — its absence is handled
        # in the key-selection logic below.
        parts = line.split("\t")
        if len(parts) < 3:
            continue  # malformed row — too few fields

        # ── Column 1: English word (canonical NRC lemma) ──────────────────
        english_word: str = parts[0].strip().lower()
        if not english_word:
            continue  # empty first column — skip

        # ── Column 2: Emotion label ───────────────────────────────────────
        emotion: str = parts[1].strip().lower()
        if emotion not in EMOTION_LABELS:
            # Unknown emotion dimension (annotation artefact, header row,
            # or future label) — skip without raising.
            continue

        # ── Column 3: Intensity score ─────────────────────────────────────
        try:
            score: float = float(parts[2].strip())
        except ValueError:
            # Non-numeric score — covers header rows (e.g. "score") and
            # any malformed numeric strings.
            continue

        # Clamp to [0, 1] to absorb any out-of-range lexicon values that
        # could skew aggregate means or trigger threshold logic.
        score = max(0.0, min(1.0, score))

        # ── Column 4: Translated word — word key selection ────────────────
        # For English files Column 4 may be missing, empty, or a copy of
        # Column 1.  We always use Column 1 for English lookups so that
        # the key precisely matches the surface form that spaCy lemmatises
        # English tokens to.
        #
        # For all other languages we prefer the translated word because
        # the tokeniser will produce target-language lemmas at query time.
        # If Column 4 is absent or blank we fall back to the English word
        # so at least some cross-lingual coverage is preserved.
        if is_english:
            word_key: str = english_word
        else:
            translated: str = parts[3].strip().lower() if len(parts) >= 4 else ""
            word_key = translated if translated else english_word

        if not word_key:
            continue  # both columns empty — skip

        # ── Duplicate handling ────────────────────────────────────────────
        # Multiple English words may share the same translation, collapsing
        # to the same (emotion, word_key) slot.  We keep the highest score
        # so the most semantically intense mapping wins.
        existing: float = result[emotion].get(word_key, -1.0)
        if score > existing:
            result[emotion][word_key] = score

    return result


def empty_affect_pack() -> AffectPack:
    """
    Return a zeroed-out AffectPack with all 8 emotion keys present but
    empty.  Used as the graceful-degradation fallback when no file is
    available for the requested language.

    Callers that need a guaranteed-safe default should call this rather
    than constructing the dict inline, so the set of recognised emotions
    stays in sync with EMOTION_LABELS automatically.
    """
    return {label: {} for label in EMOTION_LABELS}
