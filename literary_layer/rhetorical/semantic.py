"""
Literary Layer — Semantic Rhetorical Devices (Phase 5)
Detects devices that operate at the level of imagery and argumentative stance:

    Simile            — explicit comparison using the language's simile particle
                        ("like" / "wie" / "comme") or the "as…as" / "so…wie" /
                        "aussi…que" comparative pattern.

    Rhetorical Question — interrogative sentence (ends with "?") that invites
                          reflection rather than a literal answer.  Detected via
                          language-specific interrogative words + rhetorical markers.

Language-awareness (Phase 5):
    Both detectors call get_patterns(language) to obtain the correct simile
    particles, interrogative word sets, and rhetorical markers — no language-
    specific branches inside the algorithm itself.

Phase 2: English only (hardcoded en_patterns imports).
Phase 5: language parameter forwarded through get_patterns(); DE / FR added.
"""
from __future__ import annotations

from typing import List

from literary_layer.base import LiteraryFinding
from literary_layer.line_index import char_to_line
from literary_layer.rhetorical.lang import get_patterns


# ── Private helpers ────────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int) -> str:
    """Cap *text* at *max_len* chars, breaking at the last word boundary."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rsplit(" ", 1)[0] + "…"


# ── Simile ─────────────────────────────────────────────────────────────────────

def detect_simile(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
) -> List[LiteraryFinding]:
    """
    Detect similes in each sentence of *doc* using two complementary passes.

    Pass A — simile particle as ADP/SCONJ:
        Checks whether the language's simile particle ("like" / "wie" / "comme")
        appears as one of the acceptable POS tags defined in patterns.SIMILE_POS.
        This distinguishes comparative use from verbal use
        (EN: "spread like a fog" vs. "I like music"; spaCy tags them differently).

    Pass B — comparative "as…as" / "so…wie" / "aussi…que" pattern:
        Language-specific regex (patterns.AS_AS_RE) catches the three-word
        comparative frame regardless of parse-tree variation.
        Group 1 of the regex captures the quality word between the markers.

    Pass A takes priority: if a sentence matches Pass A, it is not re-checked
    for Pass B so the same sentence is never double-reported.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").  Defaults to "EN".

    Returns:
        List of LiteraryFinding objects, one per sentence containing a simile.
    """
    patterns        = get_patterns(language)
    simile_words    = patterns.SIMILE_PARTICLES
    simile_pos_set  = patterns.SIMILE_POS
    as_as_re        = patterns.AS_AS_RE
    max_len         = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        char_start_abs = start_char + sent.start_char
        char_end_abs   = start_char + sent.end_char
        line_num       = char_to_line(char_start_abs, line_index)
        raw            = sent.text.strip()
        excerpt        = _truncate(raw, max_len)

        # ── Pass A: simile particle used as comparative preposition / conjunction ──
        particle_tokens = [
            t for t in sent
            if t.text.lower() in simile_words and t.pos_ in simile_pos_set
        ]

        if particle_tokens:
            matched: List[str] = []
            pt = particle_tokens[0]   # take the first particle in the sentence

            # Token before the particle — the tenor (thing being compared)
            if pt.i > sent.start:
                matched.append(doc[pt.i - 1].text)

            matched.append(pt.text)   # the particle itself ("like" / "wie" / "comme")

            # First alphabetic token after the particle — head of the vehicle NP
            for t in doc[pt.i + 1: sent.end]:
                if t.is_alpha:
                    matched.append(t.text)
                    break

            findings.append(LiteraryFinding(
                device="simile",
                category="semantic",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=excerpt,
                matched_tokens=matched,
                confidence=0.88,
                notes=(
                    f'"{pt.text}" as comparative {pt.pos_}: '
                    f"tenor–vehicle comparison"
                ),
            ))
            continue   # sentence consumed; skip Pass B

        # ── Pass B: "as…as" / "so…wie" / "aussi…que" comparative ─────────────────
        m = as_as_re.search(raw)
        if m:
            quality = m.group(1)
            findings.append(LiteraryFinding(
                device="simile",
                category="semantic",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=excerpt,
                matched_tokens=list(m.group(0).split()[:3]),  # first 3 words of match
                confidence=0.82,
                notes=f'comparative frame — quality word(s): "{quality}"',
            ))

    return findings


# ── Rhetorical Question ────────────────────────────────────────────────────────

def detect_rhetorical_question(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
) -> List[LiteraryFinding]:
    """
    Detect rhetorical questions — interrogative sentences that invite reflection
    rather than requesting a literal answer.

    Three-stage filter applied to every sentence ending with "?":

    Stage 1 (necessary):  Sentence ends with "?".
    Stage 2 (necessary):  Contains at least one language-specific interrogative
                          word (who/what/why/… for EN; wer/was/warum/… for DE;
                          qui/que/pourquoi/… for FR).
    Stage 3 (confidence): Confidence is elevated to 0.78 when:
                          • A universal / 2nd-person subject is present
                            (anyone, everyone, nobody, man, tous, …)
                          • OR the sentence is short (≤ 8 content words).
                          Without these markers confidence stays at 0.55.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").  Defaults to "EN".

    Returns:
        List of LiteraryFinding objects (one per qualifying sentence).
    """
    patterns        = get_patterns(language)
    interrogatives  = patterns.INTERROGATIVES
    rhet_markers    = patterns.RHETORICAL_MARKERS
    max_len         = patterns.EXCERPT_MAX

    # POS tags that do not carry content for the short-sentence heuristic
    _FUNCTION_POS = frozenset({
        "DET", "ADP", "CCONJ", "SCONJ", "PART", "SPACE",
    })

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        raw = sent.text.strip()

        # Stage 1: must end with "?"
        if not raw.endswith("?"):
            continue

        alpha_tokens = [t for t in sent if t.is_alpha]

        # Stage 2: must contain at least one language-specific interrogative word
        interrogatives_found = [
            t.text for t in alpha_tokens
            if t.text.lower() in interrogatives
        ]
        if not interrogatives_found:
            continue

        # Stage 3: assess confidence
        content_words = [t for t in alpha_tokens if t.pos_ not in _FUNCTION_POS]
        has_marker    = any(t.text.lower() in rhet_markers for t in alpha_tokens)
        is_short      = len(content_words) <= 8

        confidence = 0.78 if (has_marker or is_short) else 0.55

        char_start_abs = start_char + sent.start_char
        char_end_abs   = start_char + sent.end_char
        line_num       = char_to_line(char_start_abs, line_index)

        note_parts = [f"interrogatives: {', '.join(interrogatives_found)}"]
        if has_marker:
            note_parts.append("universal/rhetorical subject present")
        if is_short:
            note_parts.append(f"short ({len(content_words)} content words)")
        if confidence < 0.70:
            note_parts.append("researcher review recommended")

        findings.append(LiteraryFinding(
            device="rhetorical_question",
            category="semantic",
            line_number=line_num,
            char_start=char_start_abs,
            char_end=char_end_abs,
            excerpt=_truncate(raw, max_len),
            matched_tokens=interrogatives_found,
            confidence=confidence,
            notes="; ".join(note_parts),
        ))

    return findings
