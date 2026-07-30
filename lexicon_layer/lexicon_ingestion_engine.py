"""
lexicon_layer/lexicon_ingestion_engine.py
═══════════════════════════════════════════════════════════════════
Unified Multilingual Lexicon Ingestion Engine
═══════════════════════════════════════════════════════════════════

Provides `LexiconIngestionEngine` — a single class that cleanly parses
BOTH NRC dataset formats used by this pipeline into validated in-memory
dictionaries, with full multilingual support and graceful English fallback.

Formats handled
───────────────
1. 8-Axis Emotion Intensity (4-column TSV):
       English_Word | Emotion | Score | Translated_Word
   Method: load_intensity_lexicon(language_code)
   Output: { word: { emotion: score, … } }

2. Ousiometric VAD (5-column TSV):
       English_Word | Valence | Arousal | Dominance | Translated_Word
   Method: load_ousiometric_lexicon(language_code)
   Output: { word: VADScores }   where VADScores = { 'v': float, 'a': float, 'd': float }

File naming convention (inside lexicon_dir)
───────────────────────────────────────────
  Intensity:   intensity_{lang_lower}.txt        e.g. intensity_ru.txt
  VAD (new):   nrc_vad_{lang_lower}.txt          e.g. nrc_vad_ru.txt
  VAD (legacy EN):  en_vad.tsv  (4-column: word | v | a | d, no translation)

Fallback chain (both methods)
──────────────────────────────
  Tier 1 — language-specific file      (intensity_ru.txt)
  Tier 2 — English combined base       (intensity_en.txt / nrc_vad_en.txt)
  Tier 3 — Legacy English VAD only     (en_vad.tsv — ousiometric loader only)
  Tier 4 — Empty dict + logged warning (file never installed)

English word-key rule (Task 3)
───────────────────────────────
Column 0 (English Word) is used as the dict key when EITHER:
  • lang_code == 'EN', OR
  • the Translated Word column is absent, empty, or blank.

Token cleansing (Task 3 — delegated to TokenCleanser)
────────────────────────────────────────────────────
  • Lowercase normalisation
  • N-gram rejection (translated cell contains spaces → skip row)
  • Noise rejection  (punctuation-heavy strings → skip row)
See lexicon_layer/token_cleanser.py for the exact rules.

Caching
───────
Results are stored in per-instance dicts:
  self._intensity_cache: { lang_upper: result_dict }
  self._vad_cache:       { lang_upper: result_dict }

This lets the engine be used as a long-lived application singleton
(instantiate once at startup, call repeatedly) while remaining
trivially testable by constructing fresh instances pointed at
temporary directories.

Usage
─────
    from lexicon_layer import LexiconIngestionEngine

    engine = LexiconIngestionEngine()          # uses default lexicon dir
    intensity = engine.load_intensity_lexicon("RU")
    vad       = engine.load_ousiometric_lexicon("AR")

    # Access a word's emotion profile:
    anger_score = intensity.get("злость", {}).get("anger", 0.0)

    # Access VAD scores for downstream PDS rotation:
    scores = vad.get("слово", {})   # {"v": 0.72, "a": 0.45, "d": 0.63}
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Tuple

from lexicon_layer.token_cleanser import TokenCleanser

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------
# Follows the project convention of named loggers so output can be
# routed, filtered, or silenced independently per environment.

logger: logging.Logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# 8-axis emotion profile for a single word.
# Keys are canonical emotion labels (lowercase), values are [0.0, 1.0].
# Emotions not present in the lexicon for this word are absent from the dict
# (sparse representation — callers should use .get(emotion, 0.0)).
EmotionProfile = Dict[str, float]

# VAD triple for a single word — raw NRC scores, NOT rotated to PDS.
# The rotation (VAD → Power/Danger/Structure) happens downstream in
# pds_layer/pds_transformer.py; this class only ingests and stores.
VADScores = Dict[str, float]   # keys: "v", "a", "d" — all in [0.0, 1.0]

# Top-level return types
IntensityLexicon = Dict[str, EmotionProfile]   # word → {emotion: score}
VADLexicon       = Dict[str, VADScores]        # word → {v, a, d}


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The 8 emotion labels recognised in Column 2 of the intensity file.
# Any row with a Column 2 value not in this set is silently skipped.
_INTENSITY_EMOTIONS: frozenset = frozenset({
    "anger", "fear", "anticipation", "trust",
    "surprise", "sadness", "joy", "disgust",
})

# Default location of all NRC lexicon files — the shared lexicons
# sub-directory used by vad_layer and pds_layer.
_DEFAULT_LEXICON_DIR: str = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "vad_layer", "lexicons")
)


# ---------------------------------------------------------------------------
# LexiconIngestionEngine
# ---------------------------------------------------------------------------

class LexiconIngestionEngine:
    """
    Unified parser for both NRC lexicon formats used in this pipeline.

    Parameters
    ----------
    lexicon_dir : str, optional
        Absolute path to the directory that holds all lexicon files.
        Defaults to `vad_layer/lexicons/` relative to this module.
        Supply a custom path during testing to avoid touching real files.
    """

    def __init__(self, lexicon_dir: Optional[str] = None) -> None:
        # Use the provided dir or fall back to the project default.
        self._lexicon_dir: str = (
            os.path.normpath(lexicon_dir) if lexicon_dir else _DEFAULT_LEXICON_DIR
        )

        # Shared token cleanser — holds only compiled regex patterns (immutable),
        # so one instance is safe to use from both loader methods.
        self._cleanser: TokenCleanser = TokenCleanser()

        # Result caches — keyed by normalised lang code (uppercase).
        # Populated lazily on the first call for each language.
        self._intensity_cache: IntensityLexicon = {}   # type: Dict[str, IntensityLexicon]
        self._vad_cache:       Dict[str, VADLexicon]   = {}

        logger.debug(
            "LexiconIngestionEngine initialised — lexicon_dir=%s",
            self._lexicon_dir,
        )

    # =========================================================================
    # Task 1 — 8-Axis Emotion Intensity Loader (4-column format)
    # =========================================================================

    def load_intensity_lexicon(self, language_code: str) -> IntensityLexicon:
        """
        Load and cache the 8-axis emotion intensity lexicon for *language_code*.

        File format (TAB-separated):
            Col 0: English Word  — canonical NRC lemma (always present)
            Col 1: Emotion       — one of the 8 recognised dimension labels
            Col 2: Score         — float in [0, 1]; higher = stronger affect
            Col 3: Translated Word — target-language lemma (blank for EN)

        Parameters
        ----------
        language_code : str
            ISO-style code, case-insensitive (EN, RU, AR, FA, KO, …).

        Returns
        -------
        IntensityLexicon — Dict[str, Dict[str, float]]
            { word: { emotion: score, … } }

            A word's entry only contains emotions that appear in the file
            for that word (sparse).  Callers should use `.get(emotion, 0.0)`.

        Caching
        ────────
        The result is stored after the first parse.  Subsequent calls for
        the same language are instant dict lookups.
        """
        lang: str = language_code.strip().upper()

        # ── Cache hit ─────────────────────────────────────────────────────
        if lang in self._intensity_cache:
            return self._intensity_cache[lang]

        # ── Resolve path with two-tier fallback ───────────────────────────
        filepath, effective_lang = self._resolve_intensity_path(lang)

        if filepath is None:
            logger.warning(
                "load_intensity_lexicon: no intensity file found for lang=%s "
                "(tried intensity_%s.txt and intensity_en.txt in %s). "
                "Returning empty lexicon — all affect scores will be 0.0.",
                lang, lang.lower(), self._lexicon_dir,
            )
            result: IntensityLexicon = {}
            self._intensity_cache[lang] = result
            return result

        logger.info(
            "load_intensity_lexicon: loading %s (effective_lang=%s)",
            filepath, effective_lang,
        )

        # ── Parse ─────────────────────────────────────────────────────────
        result = self._parse_intensity_file(filepath, effective_lang)
        self._intensity_cache[lang] = result

        logger.info(
            "load_intensity_lexicon: cached %d words for lang=%s",
            len(result), lang,
        )
        return result

    # =========================================================================
    # Task 2 — Ousiometric VAD Loader (5-column format)
    # =========================================================================

    def load_ousiometric_lexicon(self, language_code: str) -> VADLexicon:
        """
        Load and cache the Ousiometric VAD lexicon for *language_code*.

        File format (TAB-separated):
            Col 0: English Word  — canonical NRC lemma (always present)
            Col 1: Valence       — float in [0, 1]
            Col 2: Arousal       — float in [0, 1]
            Col 3: Dominance     — float in [0, 1]
            Col 4: Translated Word — target-language lemma (blank for EN)

        NOTE: This method stores raw VAD scores only.  The rotation to
        Power / Danger / Structure (Ousiometrics) is applied DOWNSTREAM
        by pds_layer/pds_transformer.py — not here.

        Parameters
        ----------
        language_code : str
            ISO-style code, case-insensitive.

        Returns
        -------
        VADLexicon — Dict[str, Dict[str, float]]
            { word: { "v": valence, "a": arousal, "d": dominance } }

        Fallback chain (three tiers)
        ────────────────────────────
        Tier 1 — nrc_vad_{lang_lower}.txt
        Tier 2 — nrc_vad_en.txt  (EN format, 4-column, no translated word)
        Tier 3 — en_vad.tsv      (legacy 4-column EN format, older installations)
        """
        lang: str = language_code.strip().upper()

        # ── Cache hit ─────────────────────────────────────────────────────
        if lang in self._vad_cache:
            return self._vad_cache[lang]

        # ── Resolve path with three-tier fallback ─────────────────────────
        filepath, effective_lang, is_legacy = self._resolve_vad_path(lang)

        if filepath is None:
            logger.warning(
                "load_ousiometric_lexicon: no VAD file found for lang=%s "
                "(tried nrc_vad_%s.txt, nrc_vad_en.txt, en_vad.tsv in %s). "
                "Returning empty lexicon.",
                lang, lang.lower(), self._lexicon_dir,
            )
            result: VADLexicon = {}
            self._vad_cache[lang] = result
            return result

        logger.info(
            "load_ousiometric_lexicon: loading %s "
            "(effective_lang=%s, legacy_format=%s)",
            filepath, effective_lang, is_legacy,
        )

        # ── Parse ─────────────────────────────────────────────────────────
        result = self._parse_vad_file(filepath, effective_lang, is_legacy)
        self._vad_cache[lang] = result

        logger.info(
            "load_ousiometric_lexicon: cached %d words for lang=%s",
            len(result), lang,
        )
        return result

    # =========================================================================
    # Cache management
    # =========================================================================

    def clear_cache(self) -> None:
        """
        Clear both in-memory caches.

        Call this after dropping new lexicon files into the lexicon directory
        during a running process so the next call re-reads from disk.
        """
        self._intensity_cache.clear()
        self._vad_cache.clear()
        logger.debug("LexiconIngestionEngine: caches cleared.")

    def cache_info(self) -> Dict[str, list]:
        """
        Return diagnostic information about what is currently cached.

        Returns
        -------
        dict with keys "intensity" and "vad", each containing a sorted
        list of language codes currently held in memory.
        """
        return {
            "intensity": sorted(self._intensity_cache.keys()),
            "vad":       sorted(self._vad_cache.keys()),
        }

    # =========================================================================
    # Private — path resolution
    # =========================================================================

    def _resolve_intensity_path(
        self, lang: str
    ) -> Tuple[Optional[str], str]:
        """
        Resolve the best-available intensity file path for *lang*.

        Returns
        ───────
        (filepath, effective_lang) where effective_lang reflects whether
        the English fallback was used (so the parser knows which column
        to use as the word key).
        """
        lang_lower: str = lang.lower()

        # Tier 1 — language-specific combined file
        if lang != "EN":
            candidate = os.path.join(
                self._lexicon_dir, f"intensity_{lang_lower}.txt"
            )
            if os.path.isfile(candidate):
                return candidate, lang

        # Tier 2 — English combined base file
        en_candidate = os.path.join(self._lexicon_dir, "intensity_en.txt")
        if os.path.isfile(en_candidate):
            if lang != "EN":
                logger.debug(
                    "_resolve_intensity_path: intensity_%s.txt not found, "
                    "falling back to intensity_en.txt",
                    lang_lower,
                )
            return en_candidate, "EN"

        return None, "EN"

    def _resolve_vad_path(
        self, lang: str
    ) -> Tuple[Optional[str], str, bool]:
        """
        Resolve the best-available VAD file path for *lang*.

        Returns
        ───────
        (filepath, effective_lang, is_legacy_format)
            is_legacy_format=True means the file is the old 4-column
            en_vad.tsv (no Translated Word column) — the parser adjusts
            its column indices accordingly.
        """
        lang_lower: str = lang.lower()

        # Tier 1 — language-specific new 5-column file
        if lang != "EN":
            candidate = os.path.join(
                self._lexicon_dir, f"nrc_vad_{lang_lower}.txt"
            )
            if os.path.isfile(candidate):
                return candidate, lang, False

        # Tier 2 — English new 4-column file (no translated word column)
        en_new = os.path.join(self._lexicon_dir, "nrc_vad_en.txt")
        if os.path.isfile(en_new):
            if lang != "EN":
                logger.debug(
                    "_resolve_vad_path: nrc_vad_%s.txt not found, "
                    "falling back to nrc_vad_en.txt",
                    lang_lower,
                )
            return en_new, "EN", False

        # Tier 3 — legacy 4-column English file (older installations)
        en_legacy = os.path.join(self._lexicon_dir, "en_vad.tsv")
        if os.path.isfile(en_legacy):
            logger.debug(
                "_resolve_vad_path: falling back to legacy en_vad.tsv "
                "(4-column format, no Translated Word column)"
            )
            return en_legacy, "EN", True

        return None, "EN", False

    # =========================================================================
    # Private — file parsers
    # =========================================================================

    def _resolve_word_key(
        self,
        english_word: str,
        translated_word: str,
        is_english: bool,
    ) -> Optional[str]:
        """
        Apply the English fallback rule (Task 3) and run TokenCleanser.

        English fallback rule
        ─────────────────────
        The translated word column is used as the dict key ONLY when:
          • is_english is False (not processing an English file), AND
          • translated_word is non-empty after stripping.
        In all other cases Column 0 (English word) is the key.

        Token cleansing
        ────────────────
        The chosen candidate is passed through TokenCleanser.cleanse():
          • Lowercased
          • Rejected if n-gram (contains spaces)
          • Rejected if punctuation-heavy (word-char ratio < 0.5)
        Returns None if the token should be skipped.
        """
        # Select the raw candidate key
        if is_english or not translated_word.strip():
            raw_key: str = english_word
        else:
            raw_key = translated_word

        # Delegate validation and normalisation to TokenCleanser
        return self._cleanser.cleanse(raw_key)

    def _parse_intensity_file(
        self, filepath: str, effective_lang: str
    ) -> IntensityLexicon:
        """
        Parse the 4-column combined intensity file at *filepath*.

        Accumulation rule
        ─────────────────
        A single word appears on multiple rows (one per emotion).  Each
        valid row ADDS to the word's EmotionProfile dict:
            result[word]["anger"] = 0.8
            result[word]["fear"]  = 0.6   ← same word, different row
        If the same (word, emotion) pair appears twice, the HIGHER score
        wins (multiple English words may map to the same translated word).

        Returns
        ───────
        IntensityLexicon — all words seen in the file that pass cleansing.
        """
        is_english: bool = effective_lang == "EN"
        result: IntensityLexicon = {}
        skipped_ngram = skipped_noise = skipped_bad_score = skipped_emotion = 0

        try:
            with open(filepath, encoding="utf-8") as fh:
                for lineno, raw_line in enumerate(fh, start=1):
                    line: str = raw_line.rstrip("\n")
                    if not line:
                        continue

                    parts = line.split("\t")

                    # ── Minimum required columns: 0, 1, 2 ─────────────────
                    if len(parts) < 3:
                        logger.debug(
                            "%s line %d: too few columns (%d) — skipped",
                            filepath, lineno, len(parts),
                        )
                        continue

                    english_word:   str = parts[0].strip().lower()
                    emotion:        str = parts[1].strip().lower()
                    translated_word: str = parts[3].strip() if len(parts) >= 4 else ""

                    # ── Validate emotion label ─────────────────────────────
                    if emotion not in _INTENSITY_EMOTIONS:
                        # Covers header row ("emotion") and unknown labels.
                        skipped_emotion += 1
                        continue

                    # ── Parse score ────────────────────────────────────────
                    try:
                        score: float = float(parts[2].strip())
                    except ValueError:
                        skipped_bad_score += 1
                        continue

                    # Clamp to [0, 1] — absorbs any out-of-range values
                    score = max(0.0, min(1.0, score))

                    # ── Resolve and cleanse the word key ───────────────────
                    word_key: Optional[str] = self._resolve_word_key(
                        english_word, translated_word, is_english
                    )

                    if word_key is None:
                        # Determine why for accurate diagnostic counts
                        raw_candidate = english_word if is_english else (translated_word or english_word)
                        if self._cleanser.is_ngram(raw_candidate.lower()):
                            skipped_ngram += 1
                        else:
                            skipped_noise += 1
                        continue

                    # ── Accumulate into the result dict ────────────────────
                    if word_key not in result:
                        result[word_key] = {}

                    # Keep the higher score on duplicate (word, emotion) pairs
                    existing: float = result[word_key].get(emotion, -1.0)
                    if score > existing:
                        result[word_key][emotion] = score

        except OSError as exc:
            logger.error(
                "_parse_intensity_file: could not read %s — %s. "
                "Returning partial result (%d words parsed before error).",
                filepath, exc, len(result),
            )

        logger.debug(
            "_parse_intensity_file %s: %d words, "
            "skipped %d n-grams / %d noisy / %d bad-scores / %d unknown-emotions",
            os.path.basename(filepath), len(result),
            skipped_ngram, skipped_noise, skipped_bad_score, skipped_emotion,
        )
        return result

    def _parse_vad_file(
        self, filepath: str, effective_lang: str, is_legacy: bool
    ) -> VADLexicon:
        """
        Parse a VAD file at *filepath*.

        Column layout — standard 5-column format (is_legacy=False):
            Col 0: English Word
            Col 1: Valence
            Col 2: Arousal
            Col 3: Dominance
            Col 4: Translated Word

        Column layout — legacy 4-column format (is_legacy=True, en_vad.tsv):
            Col 0: Word (English)
            Col 1: Valence
            Col 2: Arousal
            Col 3: Dominance
            (no Translated Word column — word key is always Col 0)

        Scores are clamped to [0.0, 1.0] after parsing.
        Duplicate word keys keep the FIRST entry seen (NRC lexicons should
        not have duplicates, but defensive code is free).

        Returns
        ───────
        VADLexicon — { word: {"v": float, "a": float, "d": float} }
        """
        is_english: bool = effective_lang == "EN"
        result: VADLexicon = {}
        skipped_ngram = skipped_noise = skipped_bad_scores = 0

        try:
            with open(filepath, encoding="utf-8") as fh:
                for lineno, raw_line in enumerate(fh, start=1):
                    line: str = raw_line.rstrip("\n")
                    if not line:
                        continue

                    parts = line.split("\t")

                    # ── Minimum column check ───────────────────────────────
                    # Need at least col 0 + 3 score columns = 4 minimum.
                    if len(parts) < 4:
                        logger.debug(
                            "%s line %d: too few columns (%d) — skipped",
                            filepath, lineno, len(parts),
                        )
                        continue

                    english_word: str = parts[0].strip().lower()

                    # ── Parse the three VAD float scores ───────────────────
                    try:
                        valence:   float = float(parts[1].strip())
                        arousal:   float = float(parts[2].strip())
                        dominance: float = float(parts[3].strip())
                    except ValueError:
                        # Header row or malformed numeric cells.
                        skipped_bad_scores += 1
                        continue

                    # Clamp all three scores to [0.0, 1.0].
                    valence   = max(0.0, min(1.0, valence))
                    arousal   = max(0.0, min(1.0, arousal))
                    dominance = max(0.0, min(1.0, dominance))

                    # ── Resolve word key ───────────────────────────────────
                    if is_legacy:
                        # Legacy 4-column format: col 0 is always the key.
                        translated_word = ""
                    else:
                        translated_word = parts[4].strip() if len(parts) >= 5 else ""

                    word_key: Optional[str] = self._resolve_word_key(
                        english_word, translated_word, is_english or is_legacy
                    )

                    if word_key is None:
                        raw_candidate = english_word if (is_english or is_legacy) else (translated_word or english_word)
                        if self._cleanser.is_ngram(raw_candidate.lower()):
                            skipped_ngram += 1
                        else:
                            skipped_noise += 1
                        continue

                    # ── Store first-seen entry for this word ───────────────
                    # VAD lexicons are expected to have unique word entries;
                    # if a duplicate occurs we keep the first row to stay
                    # deterministic rather than silently overwriting data.
                    if word_key not in result:
                        result[word_key] = {
                            "v": valence,
                            "a": arousal,
                            "d": dominance,
                        }

        except OSError as exc:
            logger.error(
                "_parse_vad_file: could not read %s — %s. "
                "Returning partial result (%d words parsed before error).",
                filepath, exc, len(result),
            )

        logger.debug(
            "_parse_vad_file %s: %d words, "
            "skipped %d n-grams / %d noisy / %d bad-score rows",
            os.path.basename(filepath), len(result),
            skipped_ngram, skipped_noise, skipped_bad_scores,
        )
        return result
