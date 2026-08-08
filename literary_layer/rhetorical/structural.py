"""
Literary Layer — Structural Rhetorical Devices (Phase 5)
Detects devices that emerge from the repetition or mirrored arrangement of
clause boundaries across consecutive sentences:

    Anaphora   — the same lemma appears at the START of successive sentences
                 ("We shall fight on the beaches, / We shall fight on the
                 landing grounds…")

    Epistrophe — the same lemma appears at the END of successive sentences
                 ("…in God we trust / …in liberty we trust")

Detection logic (shared for both devices):
    1. Collect the first (or last) CONTENT token of each sentence, where
       "content" means: alphabetic, not in SKIP_POS_BOUNDARY.
    2. Compare adjacent sentences by token lemma so inflected forms match
       ("fights"/"fought" both reduce to lemma "fight").
    3. Extend the run as far as the same lemma continues.
    4. Emit one finding per run of length ≥ min_repeat, then skip past the
       consumed sentences so overlapping pairs are not double-counted.

Phase 2: English only.
Phase 5: language parameter added; SKIP_POS_BOUNDARY loaded from get_patterns()
         so the same code runs for DE / FR without modification.
"""
from __future__ import annotations

from typing import List, Optional

from literary_layer.base import LiteraryFinding
from literary_layer.line_index import char_to_line
from literary_layer.rhetorical.lang import get_patterns


# ── Private helpers ────────────────────────────────────────────────────────────

def _first_content(sent, skip_pos: frozenset):
    """
    Return the first token in *sent* that is alphabetic and whose POS tag is
    not in *skip_pos*.  Returns None if no qualifying token exists.
    """
    for token in sent:
        if token.is_alpha and token.pos_ not in skip_pos:
            return token
    return None


def _last_content(sent, skip_pos: frozenset):
    """
    Return the last token in *sent* that is alphabetic and whose POS tag is
    not in *skip_pos*.  Returns None if no qualifying token exists.
    """
    result = None
    for token in sent:
        if token.is_alpha and token.pos_ not in skip_pos:
            result = token
    return result


def _build_excerpt(sentences: list, max_len: int) -> str:
    """
    Build a compact excerpt showing the first ~55 chars of each sentence in
    the run, joined by ' / ', capped at *max_len* total chars.
    Shows the researcher the repeating structure at a glance.
    """
    # Show at most 4 sentences to keep the card readable
    parts  = [s.text.strip()[:55] for s in sentences[:4]]
    joined = " / ".join(parts)
    if len(joined) > max_len:
        joined = joined[:max_len - 1] + "…"
    return joined


# ── Anaphora ───────────────────────────────────────────────────────────────────

def detect_anaphora(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
    min_repeat: int = 2,
) -> List[LiteraryFinding]:
    """
    Detect anaphora: the same word/lemma at the START of min_repeat or more
    consecutive sentences.

    Language-awareness added in Phase 5: SKIP_POS_BOUNDARY and EXCERPT_MAX are
    loaded from the correct language pattern module via get_patterns(language).

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").  Defaults to "EN".
        min_repeat:  Minimum run length to report (default 2 sentences).

    Returns:
        List of non-overlapping LiteraryFinding objects.
    """
    patterns  = get_patterns(language)
    skip_pos  = patterns.SKIP_POS_BOUNDARY
    max_len   = patterns.EXCERPT_MAX

    findings:  List[LiteraryFinding] = []
    sentences: List               = list(doc.sents)
    i = 0

    while i < len(sentences) - 1:
        anchor = _first_content(sentences[i], skip_pos)
        if anchor is None:
            i += 1
            continue

        anchor_lemma = anchor.lemma_.lower()

        # Greedily extend the run while successive sentences start with the same lemma
        run = [sentences[i]]
        j   = i + 1
        while j < len(sentences):
            next_tok = _first_content(sentences[j], skip_pos)
            if next_tok and next_tok.lemma_.lower() == anchor_lemma:
                run.append(sentences[j])
                j += 1
            else:
                break

        if len(run) >= min_repeat:
            char_start_abs = start_char + run[0].start_char
            char_end_abs   = start_char + run[-1].end_char
            line_num       = char_to_line(char_start_abs, line_index)

            # Collect the actual surface form used at each sentence start
            matched = [
                tok.text
                for s in run
                if (tok := _first_content(s, skip_pos)) is not None
            ]

            findings.append(LiteraryFinding(
                device="anaphora",
                category="structural",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=_build_excerpt(run, max_len),
                matched_tokens=matched,
                # Longer runs are surer signals of deliberate rhetorical choice.
                confidence=0.90 if len(run) >= 3 else 0.72,
                notes=(
                    f'"{anchor.text}" (lemma: "{anchor_lemma}") at the start '
                    f"of {len(run)} consecutive sentences"
                ),
            ))
            i = j   # skip past the consumed run to avoid overlapping pairs
        else:
            i += 1

    return findings


# ── Epistrophe ─────────────────────────────────────────────────────────────────

def detect_epistrophe(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
    min_repeat: int = 2,
) -> List[LiteraryFinding]:
    """
    Detect epistrophe: the same word/lemma at the END of min_repeat or more
    consecutive sentences.

    Language-awareness added in Phase 5: SKIP_POS_BOUNDARY and EXCERPT_MAX are
    loaded from the correct language pattern module via get_patterns(language).

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").  Defaults to "EN".
        min_repeat:  Minimum run length to report (default 2 sentences).

    Returns:
        List of non-overlapping LiteraryFinding objects.
    """
    patterns  = get_patterns(language)
    skip_pos  = patterns.SKIP_POS_BOUNDARY
    max_len   = patterns.EXCERPT_MAX

    findings:  List[LiteraryFinding] = []
    sentences: List               = list(doc.sents)
    i = 0

    while i < len(sentences) - 1:
        anchor = _last_content(sentences[i], skip_pos)
        if anchor is None:
            i += 1
            continue

        anchor_lemma = anchor.lemma_.lower()

        # Greedily extend the run while successive sentences end with the same lemma
        run = [sentences[i]]
        j   = i + 1
        while j < len(sentences):
            last_tok = _last_content(sentences[j], skip_pos)
            if last_tok and last_tok.lemma_.lower() == anchor_lemma:
                run.append(sentences[j])
                j += 1
            else:
                break

        if len(run) >= min_repeat:
            char_start_abs = start_char + run[0].start_char
            char_end_abs   = start_char + run[-1].end_char
            line_num       = char_to_line(char_start_abs, line_index)

            matched = [
                tok.text
                for s in run
                if (tok := _last_content(s, skip_pos)) is not None
            ]

            findings.append(LiteraryFinding(
                device="epistrophe",
                category="structural",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=_build_excerpt(run, max_len),
                matched_tokens=matched,
                confidence=0.88 if len(run) >= 3 else 0.70,
                notes=(
                    f'"{anchor.text}" (lemma: "{anchor_lemma}") at the end '
                    f"of {len(run)} consecutive sentences"
                ),
            ))
            i = j
        else:
            i += 1

    return findings
