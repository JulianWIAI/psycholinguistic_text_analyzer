"""
Literary Layer — Argumentation Mining Detector (Phase 7)
Classifies each sentence in the analysis window by its rhetorical appeal type
(Ethos / Pathos / Logos — Aristotle's three modes of persuasion) and by its
argumentative function (claim / premise / evidence / appeal).

Architecture:
    The detector is rule-based and uses curated pattern modules
    (en_arg_patterns, de_arg_patterns, fr_arg_patterns) loaded via a registry.
    This means it is fully interpretable and requires no ML model download,
    making it suitable for offline environments.  Because the patterns were
    designed for human review rather than precision-at-scale, confidence values
    are deliberately conservative (0.60 – 0.88).

Appeal classification (per sentence):
    1. Score each sentence for Logos, Ethos, and Pathos by counting matching
       trigger words (1 pt) and matching multi-word phrases (2 pts each).
    2. A sentence is classified to the appeal type with the highest score,
       provided that score ≥ MIN_SCORE (prevents low-signal noise).
    3. If two appeal types tie, the order Logos > Ethos > Pathos applies
       (rational argument is reported preferentially over emotional tone).

Function classification (claim / premise / evidence / appeal):
    Applied on top of the appeal type using a second pass:
    • "claim"    — sentence contains a claim opener or claim verb
    • "premise"  — sentence contains a premise marker or phrase
    • "evidence" — sentence contains an evidence introduction phrase
    • "appeal"   — none of the above (pure emotional / authority appeal)

Window-level aggregation:
    Ratios (ethos_ratio, pathos_ratio, logos_ratio) are computed as the
    proportion of classified sentences belonging to each appeal type.
    The dominant_appeal is the type with the highest ratio; if no type
    exceeds 0.40, it is labelled "balanced".

Supported languages: EN (primary), DE (primary), FR (secondary).
"""
from __future__ import annotations

import types
from typing import Dict, List, Optional

from literary_layer.base import ArgumentationFinding, ArgumentationResult
from literary_layer.line_index import char_to_line
from literary_layer.argumentation import en_arg_patterns
from literary_layer.argumentation import de_arg_patterns
from literary_layer.argumentation import fr_arg_patterns

# ── Language → pattern module registry ────────────────────────────────────────
_PATTERN_REGISTRY: Dict[str, types.ModuleType] = {
    "EN": en_arg_patterns,
    "DE": de_arg_patterns,
    "FR": fr_arg_patterns,
}

# ── Languages with dedicated argumentation pattern modules ─────────────────────
_SUPPORTED_LANGUAGES: frozenset = frozenset({"EN", "DE", "FR"})

# ── Confidence levels assigned by evidence strength ───────────────────────────
_CONF_PHRASE_MATCH:  float = 0.85   # multi-word phrase hit (strongest signal)
_CONF_MULTI_WORD:    float = 0.78   # ≥ 2 single-word trigger hits
_CONF_SINGLE_WORD:   float = 0.62   # exactly 1 single-word trigger hit


def _get_patterns(language: str) -> types.ModuleType:
    """Return the pattern module for *language*, defaulting to English."""
    return _PATTERN_REGISTRY.get(language, en_arg_patterns)


def _score_sentence(
    sent_lower: str,
    alpha_lemmas: List[str],
    patterns,
) -> Dict[str, int]:
    """
    Compute a {logos, ethos, pathos} score dict for one sentence.

    Phrase matches contribute 2 points; single-word matches contribute 1 point.
    The score dict is used to determine the dominant appeal type.

    Args:
        sent_lower:   Lowercased raw sentence string (for phrase regex).
        alpha_lemmas: List of lowercased lemmas of alpha tokens (for word hits).
        patterns:     Language-specific pattern module.

    Returns:
        Dict with keys "logos", "ethos", "pathos" and integer score values.
    """
    scores = {"logos": 0, "ethos": 0, "pathos": 0}

    # ── Logos scoring ──────────────────────────────────────────────────────────
    for phrase in patterns.LOGOS_PHRASES:
        if phrase.lower() in sent_lower:
            scores["logos"] += 2

    for lemma in alpha_lemmas:
        if lemma in patterns.LOGOS_CONNECTORS:
            scores["logos"] += 1
        if lemma in patterns.LOGOS_EVIDENCE_WORDS:
            scores["logos"] += 1
        if lemma in patterns.LOGOS_CAUSAL_VERBS:
            scores["logos"] += 1

    # ── Ethos scoring ──────────────────────────────────────────────────────────
    for phrase in patterns.ETHOS_PHRASES:
        if phrase.lower() in sent_lower:
            scores["ethos"] += 2

    for lemma in alpha_lemmas:
        if lemma in patterns.ETHOS_AUTHORITY_WORDS:
            scores["ethos"] += 1

    # ── Pathos scoring ─────────────────────────────────────────────────────────
    for phrase in patterns.PATHOS_PHRASES:
        if phrase.lower() in sent_lower:
            scores["pathos"] += 2

    for lemma in alpha_lemmas:
        if lemma in patterns.PATHOS_EMOTION_WORDS:
            scores["pathos"] += 1
        if lemma in patterns.PATHOS_INTENSIFIERS:
            scores["pathos"] += 1

    return scores


def _dominant_appeal(scores: Dict[str, int], min_score: int) -> Optional[str]:
    """
    Return the appeal type with the highest score if it meets *min_score*,
    or None if no appeal is strong enough.  Ties broken by Logos > Ethos > Pathos.
    """
    ordered = [("logos", scores["logos"]),
               ("ethos", scores["ethos"]),
               ("pathos", scores["pathos"])]
    ordered.sort(key=lambda x: x[1], reverse=True)
    if ordered[0][1] < min_score:
        return None
    return ordered[0][0]


def _detect_function(sent_lower: str, alpha_lemmas: List[str], patterns) -> str:
    """
    Classify the argumentative function of the sentence.

    Priority order: evidence > claim > premise > appeal
    (Evidence and claim are more specific, so they take precedence.)
    """
    # Evidence: multi-word phrase signals concrete empirical support
    for phrase in patterns.EVIDENCE_PHRASES:
        if phrase.lower() in sent_lower:
            return "evidence"

    # Claim: sentence asserts a position
    for opener in patterns.CLAIM_OPENERS:
        if sent_lower.startswith(opener.lower()) or opener.lower() in sent_lower[:60]:
            return "claim"
    for lemma in alpha_lemmas:
        if lemma in patterns.CLAIM_VERBS:
            return "claim"

    # Premise: sentence provides a reason / support
    for phrase in patterns.PREMISE_PHRASES:
        if phrase.lower() in sent_lower:
            return "premise"
    for lemma in alpha_lemmas:
        if lemma in patterns.PREMISE_MARKERS:
            return "premise"

    return "appeal"


def _collect_trigger_words(
    sent_lower: str,
    alpha_lemmas: List[str],
    appeal: str,
    patterns,
) -> List[str]:
    """Collect the surface trigger words/phrases that drove the classification."""
    triggers: List[str] = []

    if appeal == "logos":
        for phrase in patterns.LOGOS_PHRASES:
            if phrase.lower() in sent_lower:
                triggers.append(phrase)
        for lemma in alpha_lemmas:
            if lemma in patterns.LOGOS_CONNECTORS | patterns.LOGOS_EVIDENCE_WORDS | patterns.LOGOS_CAUSAL_VERBS:
                if lemma not in triggers:
                    triggers.append(lemma)

    elif appeal == "ethos":
        for phrase in patterns.ETHOS_PHRASES:
            if phrase.lower() in sent_lower:
                triggers.append(phrase)
        for lemma in alpha_lemmas:
            if lemma in patterns.ETHOS_AUTHORITY_WORDS and lemma not in triggers:
                triggers.append(lemma)

    elif appeal == "pathos":
        for phrase in patterns.PATHOS_PHRASES:
            if phrase.lower() in sent_lower:
                triggers.append(phrase)
        for lemma in alpha_lemmas:
            if lemma in patterns.PATHOS_EMOTION_WORDS | patterns.PATHOS_INTENSIFIERS:
                if lemma not in triggers:
                    triggers.append(lemma)

    return triggers[:8]   # cap at 8 to avoid flooding the UI chip strip


def _truncate(text: str, max_len: int = 140) -> str:
    """Cap *text* at *max_len* chars at the last word boundary."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rsplit(" ", 1)[0] + "…"


class ArgumentationDetector:
    """
    Stateless argumentation mining detector.

    Instantiate once as a singleton in LiteraryAnalyzer.__init__() and reuse
    across all windows and requests — the detector carries no per-document state.

    Usage:
        detector = ArgumentationDetector()
        result = detector.detect(doc, start_char, line_index, "EN")
    """

    def detect(
        self,
        doc,
        start_char:  int,
        line_index:  List[int],
        language:    str,
    ) -> ArgumentationResult:
        """
        Classify every sentence in *doc* by appeal type and argumentative
        function, then aggregate ratios for the window.

        Args:
            doc:         Pre-parsed spaCy Doc for the analysis window.
            start_char:  Absolute char offset of the window in the full document.
            line_index:  Pre-built char-to-line map from build_line_index().
            language:    ISO language code ("EN", "DE", "FR").

        Returns:
            ArgumentationResult with per-sentence findings and window ratios.
            Returns an empty ArgumentationResult for unsupported languages.
        """
        if language not in _SUPPORTED_LANGUAGES:
            return ArgumentationResult()

        patterns   = _get_patterns(language)
        min_score  = patterns.MIN_SCORE
        findings:  List[ArgumentationFinding] = []

        for sent in doc.sents:
            raw_text   = sent.text.strip()
            sent_lower = raw_text.lower()

            # Build lowercased lemma list for word-level matching
            alpha_lemmas = [
                t.lemma_.lower()
                for t in sent
                if t.is_alpha
            ]

            # Score the sentence against the three appeal categories
            scores  = _score_sentence(sent_lower, alpha_lemmas, patterns)
            appeal  = _dominant_appeal(scores, min_score)

            if appeal is None:
                continue   # sentence doesn't carry a detectable appeal

            # Determine argumentative function
            func = _detect_function(sent_lower, alpha_lemmas, patterns)

            # Collect the trigger words that drove the classification
            triggers = _collect_trigger_words(sent_lower, alpha_lemmas, appeal, patterns)

            # Compute confidence from the dominant score
            dom_score = scores[appeal]
            if dom_score >= 4:
                confidence = _CONF_PHRASE_MATCH
            elif dom_score >= 2:
                confidence = _CONF_MULTI_WORD
            else:
                confidence = _CONF_SINGLE_WORD

            char_start_abs = start_char + sent.start_char
            char_end_abs   = start_char + sent.end_char
            line_num       = char_to_line(char_start_abs, line_index)

            findings.append(ArgumentationFinding(
                appeal_type   = appeal,
                function      = func,
                line_number   = line_num,
                char_start    = char_start_abs,
                char_end      = char_end_abs,
                excerpt       = _truncate(raw_text),
                trigger_words = triggers,
                confidence    = confidence,
                notes=(
                    f"{appeal.upper()} {func} — "
                    f"score {dom_score} "
                    f"(logos={scores['logos']}, "
                    f"ethos={scores['ethos']}, "
                    f"pathos={scores['pathos']})"
                ),
            ))

        # ── Window-level appeal ratios ─────────────────────────────────────────
        total = max(1, len(findings))
        ethos_n  = sum(1 for f in findings if f.appeal_type == "ethos")
        pathos_n = sum(1 for f in findings if f.appeal_type == "pathos")
        logos_n  = sum(1 for f in findings if f.appeal_type == "logos")

        ethos_ratio  = ethos_n  / total
        pathos_ratio = pathos_n / total
        logos_ratio  = logos_n  / total

        # Dominant appeal: highest ratio wins; "balanced" if leader < 40%
        ratios = [("logos", logos_ratio), ("ethos", ethos_ratio), ("pathos", pathos_ratio)]
        ratios.sort(key=lambda x: x[1], reverse=True)
        dominant = ratios[0][0] if (ratios[0][1] >= 0.40 and findings) else "balanced"

        return ArgumentationResult(
            findings        = findings,
            ethos_ratio     = round(ethos_ratio,  3),
            pathos_ratio    = round(pathos_ratio, 3),
            logos_ratio     = round(logos_ratio,  3),
            dominant_appeal = dominant,
        )
