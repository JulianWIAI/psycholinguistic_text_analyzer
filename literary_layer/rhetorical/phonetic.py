"""
Literary Layer — Phonetic Rhetorical Devices (Phase 5)

Detects two classes of sound-repetition device:

    Alliteration — repetition of the initial consonant sound across content
                   words within a single sentence.  Supported for EN / DE / FR.

    Assonance    — repetition of the dominant vowel sound across content words
                   within a single sentence.  Since the engine has no phoneme
                   lookup table, the first vowel group in each word serves as a
                   proxy for the nuclear vowel — accurate enough for prose but
                   should be treated as approximate, especially for DE / FR where
                   digraphs (ei, au, eu; eau, ai, ou) are normalised.
                   Supported for EN / DE / FR.

Phase 2 history: alliteration (EN only).
Phase 5 additions: language-aware alliteration for DE / FR; new detect_assonance.
"""
from __future__ import annotations

import re
from typing import Dict, List

from literary_layer.base import LiteraryFinding
from literary_layer.line_index import char_to_line
from literary_layer.rhetorical.lang import get_patterns


# ── Private helpers ────────────────────────────────────────────────────────────

def _first_consonant(word: str, vowels: frozenset) -> str:
    """
    Return the lowercase first consonant letter of *word*, or '' if the word
    begins with a vowel or contains no alphabetic characters.
    Only the very first letter is examined — standard alliteration matches on
    the initial sound, not on the full onset cluster.
    """
    for ch in word.lower():
        if ch.isalpha():
            return "" if ch in vowels else ch
    return ""


def _dominant_vowel(word: str, vowels: frozenset) -> str:
    """
    Return the first complete vowel group in *word* as a proxy for its
    dominant nuclear vowel sound.

    Examples (EN): "fire" → "i", "flower" → "o", "through" → "ough"
    Examples (DE): "König" → "ö",  "heit" → "ei"

    Returns '' for words with no vowel (rare; usually non-alpha tokens that
    slipped through the alpha filter).
    """
    group = ""
    for ch in word.lower():
        if not ch.isalpha():
            continue
        if ch in vowels:
            group += ch
        elif group:
            # group just finished — return it
            return group
    return group   # word ends in vowel(s)


def _truncate_excerpt(text: str, max_len: int) -> str:
    """
    Return *text* capped at *max_len* chars, always breaking at a word
    boundary so no word is split mid-character.
    """
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rsplit(" ", 1)[0] + "…"


# ── Alliteration ───────────────────────────────────────────────────────────────

def detect_alliteration(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
    min_words: int = 3,
) -> List[LiteraryFinding]:
    """
    Scan each sentence in *doc* for alliteration and return one LiteraryFinding
    per alliterative group found.

    Language-awareness added in Phase 5: VOWELS and SKIP_POS_ALLITERATION are
    loaded from the correct language pattern module via get_patterns(language).

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of this window in the full document.
        line_index:  Pre-built list of line-start offsets from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").  Defaults to "EN".
        min_words:   Minimum matching content tokens required (default 3).

    Returns:
        List of LiteraryFinding objects sorted by position in the window.
    """
    patterns  = get_patterns(language)
    vowels    = patterns.VOWELS
    skip_pos  = patterns.SKIP_POS_ALLITERATION
    max_len   = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        # Gather multi-character alpha tokens
        alpha_tokens = [t for t in sent if t.is_alpha and len(t.text) > 1]
        if len(alpha_tokens) < min_words:
            continue

        # Group content tokens (non-function-word) by initial consonant
        groups: Dict[str, list] = {}
        for token in alpha_tokens:
            if token.pos_ in skip_pos:
                continue
            ic = _first_consonant(token.text, vowels)
            if not ic:
                continue     # word starts with a vowel
            groups.setdefault(ic, []).append(token)

        # Emit a finding for every consonant with enough matching words
        for consonant, tokens in groups.items():
            if len(tokens) < min_words:
                continue

            char_start_abs = start_char + sent.start_char
            char_end_abs   = start_char + sent.end_char
            line_num       = char_to_line(char_start_abs, line_index)

            findings.append(LiteraryFinding(
                device="alliteration",
                category="phonetic",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=_truncate_excerpt(sent.text.strip(), max_len),
                matched_tokens=[t.text for t in tokens],
                # Confidence grows with the number of matching words,
                # capped at 0.97 — high but not certain for automated detection.
                confidence=min(0.97, 0.60 + len(tokens) * 0.10),
                notes=(
                    f"{len(tokens)} /{consonant}/-initial content words "
                    f"in one sentence"
                ),
            ))

    return findings


# ── Assonance ──────────────────────────────────────────────────────────────────

def detect_assonance(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
    min_words: int = 3,
) -> List[LiteraryFinding]:
    """
    Scan each sentence in *doc* for assonance — the deliberate repetition of
    the same vowel sound across content words.

    Since the engine has no phoneme lookup table, the first vowel group in each
    word (extracted by _dominant_vowel) serves as a proxy for the nuclear vowel.
    This is accurate for clear cases ("beat / lean / dream" all yield "ea") but
    may miss dialect-dependent pronunciations or vowel digraphs that represent
    different sounds in the same orthographic pattern.

    Confidence is capped at 0.78 (lower than alliteration) because the letter-
    proxy can conflate different vowel phonemes that happen to share spelling
    (e.g. English "bread" and "bead" both yield "ea" but sound different).

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of this window in the full document.
        line_index:  Pre-built list of line-start offsets from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").  Defaults to "EN".
        min_words:   Minimum content tokens sharing a vowel group (default 3).

    Returns:
        List of LiteraryFinding objects sorted by position in the window.
    """
    patterns  = get_patterns(language)
    vowels    = patterns.VOWELS
    skip_pos  = patterns.SKIP_POS_ALLITERATION   # same exclusion logic as alliteration
    max_len   = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        # Gather multi-character alpha content tokens
        alpha_tokens = [
            t for t in sent
            if t.is_alpha and len(t.text) > 2 and t.pos_ not in skip_pos
        ]
        if len(alpha_tokens) < min_words:
            continue

        # Group by dominant vowel group (proxy for vowel sound)
        groups: Dict[str, list] = {}
        for token in alpha_tokens:
            dv = _dominant_vowel(token.text, vowels)
            if not dv:
                continue
            groups.setdefault(dv, []).append(token)

        # Emit a finding for every vowel group with enough matches
        for vowel_group, tokens in groups.items():
            if len(tokens) < min_words:
                continue

            char_start_abs = start_char + sent.start_char
            char_end_abs   = start_char + sent.end_char
            line_num       = char_to_line(char_start_abs, line_index)

            findings.append(LiteraryFinding(
                device="assonance",
                category="phonetic",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=_truncate_excerpt(sent.text.strip(), max_len),
                matched_tokens=[t.text for t in tokens],
                # Lower ceiling than alliteration — vowel-group proxy is imprecise.
                confidence=min(0.78, 0.52 + len(tokens) * 0.08),
                notes=(
                    f"{len(tokens)} words share vowel group /{vowel_group}/ "
                    f"(orthographic proxy for vowel sound)"
                ),
            ))

    return findings
