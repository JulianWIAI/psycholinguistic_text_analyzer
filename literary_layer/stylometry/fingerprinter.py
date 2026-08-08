"""
Literary Layer — Stylometric Fingerprinter (Phase 8)
Computes an authorship fingerprint for one analysis window, producing metrics
that characterise a writer's style independently of content.

The core output is a Burrows'-Delta-compatible function-word frequency profile:
normalised occurrence rates of the top function words in the language.  When
multiple windows or documents are compared, their profiles can be used to
compute Delta distances for authorship attribution studies.

Additional stylometric dimensions:
    Punctuation profile  — comma / period / semicolon / exclamation / question
                           mark counts per 1000 words, signalling syntactic
                           complexity and emotional register.
    Sentence-length stats — mean, std, min, max, coefficient of variation.
                            High CV (std/mean) → varied, dynamic syntax;
                            Low CV → metronomic, formulaic style.
    Word-length profile  — mean char length, short-word ratio (≤3 chars),
                            medium-word ratio (4–6 chars), long-word ratio (≥7).
                            High long-word ratio correlates with academic register.
    Hapax legomena ratio — unique-occurrence words / total unique words.
                           High → lexically inventive; Low → restricted vocabulary.
    Raw TTR             — simple type / token ratio for the window.

Languages: EN / DE / FR (function-word list switches per language).
"""
from __future__ import annotations

import math
from typing import Dict, List

from literary_layer.base import StylometricResult
from literary_layer.stylometry import en_function_words
from literary_layer.stylometry import de_function_words
from literary_layer.stylometry import fr_function_words

# ── Function-word registry ─────────────────────────────────────────────────────
_FW_REGISTRY: Dict[str, List[str]] = {
    "EN": en_function_words.FUNCTION_WORDS,
    "DE": de_function_words.FUNCTION_WORDS,
    "FR": fr_function_words.FUNCTION_WORDS,
}

# ── Punctuation marks to profile ───────────────────────────────────────────────
# Mapped to a reader-friendly label for the to_dict / UI output.
_PUNCT_MAP: Dict[str, str] = {
    ",":  "comma",
    ".":  "period",
    ";":  "semicolon",
    "!":  "exclamation",
    "?":  "question",
    "—":  "em_dash",
    "–":  "en_dash",
    ":":  "colon",
}


class StylometricFingerprinter:
    """
    Stateless stylometric analyzer.

    Instantiate once as a singleton in LiteraryAnalyzer.__init__() and reuse
    across all windows — the fingerprinter carries no per-document state.

    Usage:
        fp = StylometricFingerprinter()
        result = fp.compute(doc, "EN")
    """

    def compute(self, doc, language: str) -> StylometricResult:
        """
        Compute the full stylometric fingerprint for *doc*.

        Args:
            doc:       Pre-parsed spaCy Doc for the analysis window.
            language:  ISO language code ("EN", "DE", "FR").

        Returns:
            StylometricResult with all fields populated.
            Falls back to EN function-word list for unsupported languages.
        """
        fw_list = _FW_REGISTRY.get(language, en_function_words.FUNCTION_WORDS)

        # Collect basic token lists once — reused by all metric methods
        all_tokens   = list(doc)
        alpha_tokens = [t for t in all_tokens if t.is_alpha]
        punct_tokens = [t for t in all_tokens if t.is_punct or t.text in _PUNCT_MAP]

        n_words = max(1, len(alpha_tokens))

        return StylometricResult(
            function_word_profile  = self._function_word_profile(alpha_tokens, fw_list, n_words),
            punctuation_ratios     = self._punctuation_ratios(all_tokens, n_words),
            sentence_length_stats  = self._sentence_length_stats(doc),
            word_length_stats      = self._word_length_stats(alpha_tokens),
            hapax_ratio            = self._hapax_ratio(alpha_tokens),
            type_token_ratio       = self._ttr(alpha_tokens),
        )

    # ── Private metric methods ─────────────────────────────────────────────────

    def _function_word_profile(
        self,
        alpha_tokens: list,
        fw_list: List[str],
        n_words: int,
    ) -> Dict[str, float]:
        """
        Compute normalised occurrence rate (per 1000 words) for each function word.

        Only words that appear at least once in the window are included in the
        output dict so the result stays sparse and readable.  Words with 0
        occurrences are simply absent from the dict; the UI should treat a
        missing word as 0.
        """
        # Build a lowercased frequency counter for all alpha tokens
        freq: Dict[str, int] = {}
        for t in alpha_tokens:
            w = t.text.lower()
            freq[w] = freq.get(w, 0) + 1

        per_1000 = 1000.0 / n_words
        profile: Dict[str, float] = {}
        for fw in fw_list:
            count = freq.get(fw, 0)
            if count > 0:
                profile[fw] = round(count * per_1000, 2)

        return profile

    def _punctuation_ratios(
        self,
        all_tokens: list,
        n_words: int,
    ) -> Dict[str, float]:
        """
        Count each tracked punctuation mark and normalise per 1000 words.

        Counts are taken from spaCy tokens (not raw text) so multi-character
        tokens like ellipsis "..." are handled consistently.
        """
        counts: Dict[str, int] = {label: 0 for label in _PUNCT_MAP.values()}
        for t in all_tokens:
            label = _PUNCT_MAP.get(t.text)
            if label:
                counts[label] = counts.get(label, 0) + 1

        per_1000 = 1000.0 / n_words
        return {label: round(count * per_1000, 2) for label, count in counts.items()}

    def _sentence_length_stats(self, doc) -> Dict[str, float]:
        """
        Compute descriptive statistics over sentence lengths (alpha token count).

        Returns mean, std, min, max, and coefficient of variation (cv = std/mean).
        A high CV indicates stylistically varied sentence lengths; a low CV
        indicates a metronomic, regular sentence rhythm.
        """
        lengths = [
            sum(1 for t in sent if t.is_alpha)
            for sent in doc.sents
        ]
        if not lengths:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "cv": 0.0}

        mean = sum(lengths) / len(lengths)
        variance = sum((x - mean) ** 2 for x in lengths) / max(1, len(lengths))
        std  = math.sqrt(variance)
        cv   = std / mean if mean > 0 else 0.0

        return {
            "mean": round(mean, 2),
            "std":  round(std,  2),
            "min":  float(min(lengths)),
            "max":  float(max(lengths)),
            "cv":   round(cv, 3),
        }

    def _word_length_stats(self, alpha_tokens: list) -> Dict[str, float]:
        """
        Compute word-length profile: mean char length and three ratio bands.

        short_ratio  — words of ≤ 3 chars (articles, prepositions, short verbs)
        medium_ratio — words of 4–6 chars (core vocabulary)
        long_ratio   — words of ≥ 7 chars (academic, technical, Latinate vocabulary)
        """
        if not alpha_tokens:
            return {"mean": 0.0, "short_ratio": 0.0, "medium_ratio": 0.0, "long_ratio": 0.0}

        lengths  = [len(t.text) for t in alpha_tokens]
        mean     = sum(lengths) / len(lengths)
        short    = sum(1 for l in lengths if l <= 3)
        medium   = sum(1 for l in lengths if 4 <= l <= 6)
        long_    = sum(1 for l in lengths if l >= 7)
        n        = len(lengths)

        return {
            "mean":         round(mean, 2),
            "short_ratio":  round(short  / n, 3),
            "medium_ratio": round(medium / n, 3),
            "long_ratio":   round(long_  / n, 3),
        }

    def _hapax_ratio(self, alpha_tokens: list) -> float:
        """
        Compute the hapax legomena ratio.

        Hapax legomena are word forms that appear exactly once in the window.
        High ratio → lexically inventive / creative.
        Low ratio  → restricted vocabulary / formulaic or repetitive text.

        Returns hapax_count / unique_types; 0.0 for empty input.
        """
        if not alpha_tokens:
            return 0.0

        freq: Dict[str, int] = {}
        for t in alpha_tokens:
            w = t.text.lower()
            freq[w] = freq.get(w, 0) + 1

        unique = len(freq)
        hapax  = sum(1 for count in freq.values() if count == 1)
        return round(hapax / max(1, unique), 3)

    def _ttr(self, alpha_tokens: list) -> float:
        """Compute raw type-token ratio (unique forms / total tokens)."""
        if not alpha_tokens:
            return 0.0
        forms  = set(t.text.lower() for t in alpha_tokens)
        return round(len(forms) / len(alpha_tokens), 3)
