"""
Literary Layer — Narrative Analyzer (Phase 4)
Computes aggregate narrative and stylistic metrics for one analysis window
from an already-parsed spaCy Doc.  All metrics are aggregate (window-level),
not per-finding — they describe the *texture* of the passage rather than
locating specific devices.

Metrics computed:
    Voice               — 1st / 2nd / 3rd person pronoun distribution
    Tense               — Past / Present / Future verb ratio
    Direct Speech Ratio — proportion of chars inside quotation marks
    Mean Sentence Length— average number of tokens per sentence
    MATTR               — Moving-Average Type-Token Ratio (lexical richness)
    Subordination Ratio — subordinate-clause dependency arcs per sentence
    Readability Score   — Flesch Reading Ease for EN; 0.0 for other languages

All metrics except readability work for any spaCy-supported language.
Tense detection relies on spaCy morphology, which varies in quality across
language models — results for non-EN languages should be interpreted with care.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

from literary_layer.base import NarrativeResult
from literary_layer.narrative.readability import (
    compute_mattr,
    # English
    count_syllables,
    flesch_reading_ease,
    # German (Phase 6)
    count_syllables_de,
    amstad_readability,
    # French (Phase 6)
    count_syllables_fr,
    kandel_moles_readability,
)

# ── Pronoun sets for voice detection ──────────────────────────────────────────
# English pronouns only.  For DE/FR voice detection the POS-based pronoun
# filter below catches pronouns in any language without needing a word list.

_FIRST_PERSON: frozenset = frozenset({
    "i", "me", "my", "mine", "myself",
    "we", "us", "our", "ours", "ourselves",
})
_SECOND_PERSON: frozenset = frozenset({
    "you", "your", "yours", "yourself", "yourselves",
})
_THIRD_PERSON: frozenset = frozenset({
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
})

# ── Future-tense modal markers ─────────────────────────────────────────────────
# "will" and "shall" reliably signal future reference in any EN context.
# "'ll" appears as a separate token after elision ("he'll" → "he" + "'ll").
_FUTURE_MODALS: frozenset = frozenset({"will", "shall", "'ll"})

# ── Dependency relations that mark subordinate clauses ─────────────────────────
# These arcs on a verb token indicate it heads a subordinate clause.
_SUBORDINATE_DEPS: frozenset = frozenset({
    "advcl",   # adverbial clause
    "relcl",   # relative clause
    "csubj",   # clausal subject
    "ccomp",   # clausal complement
    "xcomp",   # open clausal complement
})

# ── Quotation mark patterns for direct speech detection ───────────────────────
# Covers straight quotes ("…"), curly quotes ("…" / '…'), and guillemets («…»)
_QUOTE_RE = re.compile(
    r'"[^"]*"'           # straight double quotes
    r'|“[^”]*”'  # "…"  curly double
    r"|‘[^’]*’"  # '…'  curly single
    r"|«[^»]*»",         # «…»  guillemets
    re.DOTALL,
)


class NarrativeAnalyzer:
    """
    Stateless analyzer: accepts a spaCy Doc and returns a NarrativeResult.
    Instantiate once as a singleton in LiteraryAnalyzer.__init__().
    """

    # ── Public API ─────────────────────────────────────────────────────────────

    def analyze(
        self,
        doc,
        raw_text: str,
        language: str,
    ) -> NarrativeResult:
        """
        Compute all narrative metrics for one window and return a NarrativeResult.

        Args:
            doc:       spaCy Doc (pre-parsed by the macro analyzer).
            raw_text:  Raw window text string (used for direct-speech detection
                       via regex — independent of the tokenization).
            language:  ISO language code ("EN", "DE", "FR", …).

        Returns:
            NarrativeResult with all fields populated.
        """
        return NarrativeResult(
            voice=self._voice(doc),
            tense=self._tense(doc),
            direct_speech_ratio=self._direct_speech(raw_text),
            mean_sentence_length=self._mean_sentence_length(doc),
            type_token_ratio=self._mattr(doc),
            subordination_ratio=self._subordination(doc),
            readability_score=self._readability(doc, language),
        )

    # ── Private metric methods ─────────────────────────────────────────────────

    def _voice(self, doc) -> Dict[str, float]:
        """
        Compute first / second / third person pronoun distribution.

        Tokens with POS == PRON are collected and compared to the three
        pronoun sets.  Ratios are normalised by total pronouns found.
        If no pronouns are present all three ratios are 0.0.
        """
        first = second = third = 0

        for token in doc:
            if token.pos_ != "PRON":
                continue
            lower = token.text.lower()
            if lower in _FIRST_PERSON:
                first += 1
            elif lower in _SECOND_PERSON:
                second += 1
            elif lower in _THIRD_PERSON:
                third += 1

        total = first + second + third
        if total == 0:
            return {"first_person": 0.0, "second_person": 0.0, "third_person": 0.0}

        return {
            "first_person":  round(first  / total, 3),
            "second_person": round(second / total, 3),
            "third_person":  round(third  / total, 3),
        }

    def _tense(self, doc) -> Dict[str, float]:
        """
        Compute past / present / future verb tense distribution.

        Uses spaCy morphological analysis:
            • Tense=Past  → past
            • Tense=Pres  → present
            • Modal "will" / "shall" / "'ll" heading a VP → future

        Ratios are normalised by the total number of categorised verbs.
        """
        past = pres = future = 0

        for token in doc:
            if token.pos_ not in ("VERB", "AUX"):
                continue

            tense_feat = token.morph.get("Tense")

            if "Past" in tense_feat:
                past += 1
            elif "Pres" in tense_feat:
                pres += 1
            elif token.text.lower() in _FUTURE_MODALS:
                # Count each modal once; its dependent infinitive is not double-counted
                future += 1

        total = past + pres + future
        if total == 0:
            return {"past": 0.0, "present": 0.0, "future": 0.0}

        return {
            "past":    round(past   / total, 3),
            "present": round(pres   / total, 3),
            "future":  round(future / total, 3),
        }

    def _direct_speech(self, raw_text: str) -> float:
        """
        Return the proportion of *raw_text* chars that fall inside quotation marks.

        Covers straight double quotes, curly double and single quotes, and guillemets.
        Returns 0.0 for empty text or texts with no detected quotations.
        """
        if not raw_text:
            return 0.0

        quoted_chars = sum(len(m.group()) for m in _QUOTE_RE.finditer(raw_text))
        return round(quoted_chars / len(raw_text), 3)

    def _mean_sentence_length(self, doc) -> float:
        """
        Compute the mean number of alpha tokens per sentence.
        Excludes punctuation and whitespace tokens for a clean word count.
        """
        sentence_lengths: List[int] = [
            sum(1 for t in sent if t.is_alpha)
            for sent in doc.sents
        ]
        if not sentence_lengths:
            return 0.0
        return round(sum(sentence_lengths) / len(sentence_lengths), 1)

    def _mattr(self, doc) -> float:
        """
        Compute the Moving-Average Type-Token Ratio (MATTR) from the
        lowercased lemma forms of all alpha content tokens.
        Using lemmas rather than surface forms avoids inflection noise
        ("run" and "ran" count as the same type).
        """
        tokens = [
            token.lemma_.lower()
            for token in doc
            if token.is_alpha and not token.is_stop and len(token.text) > 1
        ]
        return round(compute_mattr(tokens), 3)

    def _subordination(self, doc) -> float:
        """
        Compute the subordination ratio: number of subordinate-clause
        dependency arcs divided by number of sentences.

        A higher ratio suggests a more complex, periodic syntactic style;
        a lower ratio suggests a paratactic or cumulative style.
        """
        sub_count  = sum(1 for t in doc if t.dep_ in _SUBORDINATE_DEPS)
        sent_count = sum(1 for _ in doc.sents)
        return round(sub_count / max(1, sent_count), 3)

    def _readability(self, doc, language: str) -> float:
        """
        Compute a language-specific readability score (Phase 6).

        Dispatch table:
            EN — Flesch Reading Ease   (Flesch 1948):   206.835 − 1.015·ASL − 84.6·ASW
            DE — Amstad formula        (Amstad 1978):   180 − ASL − 58.5·ASW
            FR — Kandel-Moles formula  (K-M 1958):      207 − 1.015·ASL − 73.6·ASW

        All three formulas share the "higher = easier" orientation.
        Returns 0.0 for any other language code.
        """
        if language not in ("EN", "DE", "FR"):
            return 0.0

        n_sentences = sum(1 for _ in doc.sents)
        words: List[str] = [t.text for t in doc if t.is_alpha]

        if language == "EN":
            n_syllables = sum(count_syllables(w) for w in words)
            return flesch_reading_ease(n_sentences, words, n_syllables)

        if language == "DE":
            # Use the umlaut-aware German syllable counter
            n_syllables = sum(count_syllables_de(w) for w in words)
            return amstad_readability(n_sentences, words, n_syllables)

        # FR
        # Use the accent-aware French syllable counter
        n_syllables = sum(count_syllables_fr(w) for w in words)
        return kandel_moles_readability(n_sentences, words, n_syllables)
