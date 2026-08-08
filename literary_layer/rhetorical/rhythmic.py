"""
Literary Layer — Rhythmic Rhetorical Devices (Phase 6)
Detects four devices that shape the rhythm and rhetorical impact of prose by
manipulating the presence, absence, and repetition of grammatical connectors:

    Polysyndeton — deliberate repetition of the same coordinating conjunction
                   (and / or / nor …) three or more times within a sentence,
                   creating a cumulative, breathless, or insistent effect.
                   Supported: EN / DE / FR.

    Asyndeton    — deliberate omission of any coordinating conjunction in a
                   comma-separated list of three or more items, producing a
                   rapid, staccato rhythm ("I came, I saw, I conquered").
                   Supported: EN / DE / FR (comma is universal punctuation).

    Hyperbole    — deliberate exaggeration for rhetorical effect, detected via:
                   Pattern A: superlative adjective + extent phrase
                              ("the greatest ever", "worst in history").
                   Pattern B: quantitative exaggeration phrase
                              ("a million times", "for a thousand years",
                               "the whole world").
                   Currently English-only; DE / FR patterns to be added in
                   Phase 7.

    Litotes      — understatement through negation of an opposite quality:
                   "not bad" (= good), "not uncommon" (= common).
                   Detected by finding "not" (PART) immediately before an
                   adjective / adverb whose lemma carries a negative quality
                   (either by negative prefix un-/in-/im-/dis- or explicit
                   negative lemma in a curated set).
                   Currently English-only.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

from literary_layer.base import LiteraryFinding
from literary_layer.line_index import char_to_line
from literary_layer.rhetorical.lang import get_patterns


# ── Hyperbole constants (EN) ───────────────────────────────────────────────────

# Regex matching common phrases that signal extreme exaggeration of quantity
# or temporal extent.
_HYPER_QUANTITY_RE: re.Pattern = re.compile(
    r"\b(?:"
    r"(?:a\s+)?(?:million|billion|thousand|trillion|hundred)\s+times?"
    r"|for\s+(?:a\s+)?(?:thousand|million|billion)\s+years?"
    r"|forever\s+and\s+(?:a\s+day|ever)"
    r"|the\s+(?:whole|entire)\s+(?:world|universe|earth)"
    r")\b",
    re.IGNORECASE,
)

# Regex matching extent phrases that follow a superlative to signal hyperbole
# (e.g. "the best ever", "the worst in history").
_HYPER_EXTENT_RE: re.Pattern = re.compile(
    r"\b(?:"
    r"in\s+(?:the\s+)?(?:world|history|existence|all\s+creation)"
    r"|of\s+all\s+time"
    r"|ever(?:\s+made|\s+seen|\s+written|\s+lived)?"
    r"|since\s+(?:the\s+)?(?:beginning|dawn)\s+of\s+(?:time|history)"
    r")\b",
    re.IGNORECASE,
)


# ── Litotes constants (EN) ─────────────────────────────────────────────────────

# Negative prefixes — "not uncommon" → negating the negative prefix inverts
# the meaning upward (litotes).
_NEGATIVE_PREFIXES: tuple = ("un", "in", "im", "ir", "il", "dis", "non")

# Explicit negative-quality lemmas — "not bad" is a classic litotes.
_NEGATIVE_BASE_LEMMAS: frozenset = frozenset({
    "bad", "ugly", "wrong", "poor", "terrible", "horrible", "awful",
    "stupid", "worthless", "useless", "mean", "cruel", "unpleasant",
    "ordinary", "common", "unremarkable", "insignificant",
})


# ── Private helpers ────────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int) -> str:
    """Cap *text* at *max_len* chars, breaking at the last word boundary."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rsplit(" ", 1)[0] + "…"


def _content_tokens(span, skip_pos: frozenset) -> list:
    """Return alpha tokens in *span* whose POS is not in *skip_pos*."""
    return [t for t in span if t.is_alpha and t.pos_ not in skip_pos]


# ── Polysyndeton ───────────────────────────────────────────────────────────────

def detect_polysyndeton(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
    min_count: int = 3,
) -> List[LiteraryFinding]:
    """
    Detect polysyndeton: ≥ min_count occurrences of the SAME coordinating
    conjunction within a single sentence.

    Language-aware: POLYSYNDETON_CONJ and EXCERPT_MAX are loaded from the
    language pattern module via get_patterns(language).

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").
        min_count:   Minimum repetitions of the same conjunction (default 3).

    Returns:
        List of LiteraryFinding objects, one per sentence with polysyndeton.
    """
    patterns  = get_patterns(language)
    conj_set  = patterns.POLYSYNDETON_CONJ
    max_len   = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        # Collect CCONJ tokens whose surface form is in the language's conj set
        conj_tokens = [
            t for t in sent
            if t.pos_ == "CCONJ" and t.text.lower() in conj_set
        ]
        if len(conj_tokens) < min_count:
            continue

        # Group by surface form; report for any conjunction that repeats enough
        by_word: Dict[str, list] = {}
        for t in conj_tokens:
            by_word.setdefault(t.text.lower(), []).append(t)

        for word, tokens in by_word.items():
            if len(tokens) < min_count:
                continue

            char_start_abs = start_char + sent.start_char
            char_end_abs   = start_char + sent.end_char
            line_num       = char_to_line(char_start_abs, line_index)

            findings.append(LiteraryFinding(
                device="polysyndeton",
                category="rhythmic",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=_truncate(sent.text.strip(), max_len),
                matched_tokens=[t.text for t in tokens],
                # More repetitions = more deliberate rhetorical choice
                confidence=min(0.92, 0.68 + len(tokens) * 0.06),
                notes=(
                    f'"{word}" repeated {len(tokens)}× in one sentence — '
                    f"cumulative / insistent rhythm"
                ),
            ))
            break   # one finding per sentence

    return findings


# ── Asyndeton ──────────────────────────────────────────────────────────────────

def detect_asyndeton(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
    min_items: int = 3,
) -> List[LiteraryFinding]:
    """
    Detect asyndeton: ≥ min_items comma-separated clauses or items with NO
    coordinating conjunction anywhere in the sentence, producing a staccato
    rapid-list effect.

    Algorithm:
        1. Count commas in the sentence.
        2. Count CCONJ tokens in the sentence.
        3. Fire if commas ≥ min_items − 1 AND CCONJ count == 0.
        4. Collect the first content token of each comma-delimited segment as
           matched_tokens to show the researcher the list structure.

    Language-aware: uses get_patterns() for POLYSYNDETON_CONJ (to exclude sentences
    that have conjunctions not caught by spaCy's CCONJ tagger) and EXCERPT_MAX.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").
        min_items:   Minimum list items (default 3 → at least 2 commas).

    Returns:
        List of LiteraryFinding objects.
    """
    patterns = get_patterns(language)
    conj_set = patterns.POLYSYNDETON_CONJ
    max_len  = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        tokens = list(sent)

        # Count commas within the sentence
        commas = [t for t in tokens if t.is_punct and t.text == ","]
        if len(commas) < min_items - 1:
            continue

        # Any CCONJ or known conjunction word disqualifies — sentence uses coordination
        has_conj = any(
            t.pos_ == "CCONJ" or t.text.lower() in conj_set
            for t in tokens
        )
        if has_conj:
            continue

        # Collect the first alpha token from each comma-delimited segment
        segments: List[str] = []
        seg_start = sent.start
        for comma in commas:
            seg = [t for t in doc[seg_start:comma.i] if t.is_alpha]
            if seg:
                segments.append(seg[0].text)
            seg_start = comma.i + 1
        # Last segment after final comma
        last_seg = [t for t in doc[seg_start:sent.end] if t.is_alpha]
        if last_seg:
            segments.append(last_seg[0].text)

        if len(segments) < min_items:
            continue

        char_start_abs = start_char + sent.start_char
        char_end_abs   = start_char + sent.end_char
        line_num       = char_to_line(char_start_abs, line_index)

        findings.append(LiteraryFinding(
            device="asyndeton",
            category="rhythmic",
            line_number=line_num,
            char_start=char_start_abs,
            char_end=char_end_abs,
            excerpt=_truncate(sent.text.strip(), max_len),
            matched_tokens=segments,
            confidence=0.80,
            notes=(
                f"{len(segments)}-item comma list with no coordinating "
                f"conjunction — rapid, staccato rhythm"
            ),
        ))

    return findings


# ── Hyperbole (EN) ─────────────────────────────────────────────────────────────

def detect_hyperbole(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
) -> List[LiteraryFinding]:
    """
    Detect hyperbole — deliberate exaggeration for rhetorical effect.

    Two detection patterns (applied to the raw sentence text):

    Pattern A — Superlative + extent phrase:
        A superlative-degree adjective (morph Degree=Sup) appears in the same
        sentence as an extent phrase matched by _HYPER_EXTENT_RE
        ("the greatest poet ever", "the worst film in history").
        Confidence: 0.82.

    Pattern B — Quantitative exaggeration phrase:
        A fixed exaggeration phrase matched by _HYPER_QUANTITY_RE independent
        of superlatives ("a million times", "the whole world", …).
        Confidence: 0.75.

    Pattern A takes priority; a sentence is not double-reported.

    Currently English-only.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code (only "EN" supported).

    Returns:
        List of LiteraryFinding objects; empty for non-EN languages.
    """
    if language != "EN":
        return []

    patterns = get_patterns(language)
    max_len  = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        raw = sent.text.strip()

        # ── Pattern A: superlative + extent phrase ─────────────────────────────
        superlatives = [
            t for t in sent
            if t.pos_ == "ADJ" and "Sup" in t.morph.get("Degree")
        ]
        extent_match = _HYPER_EXTENT_RE.search(raw)

        if superlatives and extent_match:
            char_start_abs = start_char + sent.start_char
            char_end_abs   = start_char + sent.end_char
            line_num       = char_to_line(char_start_abs, line_index)

            findings.append(LiteraryFinding(
                device="hyperbole",
                category="rhythmic",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=_truncate(raw, max_len),
                matched_tokens=[t.text for t in superlatives] + [extent_match.group()],
                confidence=0.82,
                notes=(
                    f'superlative "{superlatives[0].text}" + '
                    f'extent phrase "{extent_match.group()}"'
                ),
            ))
            continue   # sentence consumed

        # ── Pattern B: quantitative exaggeration phrase ────────────────────────
        qty_match = _HYPER_QUANTITY_RE.search(raw)
        if qty_match:
            char_start_abs = start_char + sent.start_char
            char_end_abs   = start_char + sent.end_char
            line_num       = char_to_line(char_start_abs, line_index)

            findings.append(LiteraryFinding(
                device="hyperbole",
                category="rhythmic",
                line_number=line_num,
                char_start=char_start_abs,
                char_end=char_end_abs,
                excerpt=_truncate(raw, max_len),
                matched_tokens=qty_match.group().split(),
                confidence=0.75,
                notes=f'quantitative exaggeration: "{qty_match.group()}"',
            ))

    return findings


# ── Litotes (EN) ───────────────────────────────────────────────────────────────

def detect_litotes(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
) -> List[LiteraryFinding]:
    """
    Detect litotes — understatement achieved by negating an opposite quality:
    "not bad" (= good), "not uncommon" (= common), "not without merit".

    Algorithm:
        1. Find every "not" token whose POS is PART.
        2. Inspect the next 1–3 tokens for an adjective or adverb (ADJ / ADV).
        3. Check whether the adjective's lemma:
           (a) begins with a negative prefix (un-, in-, im-, ir-, il-, dis-, non-)
               → Confidence 0.80 (double negation is a clear litotes signal).
           (b) is in the _NEGATIVE_BASE_LEMMAS set ("not bad", "not wrong")
               → Confidence 0.70 (negating a negative adjective implies positive).

    Currently English-only.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code (only "EN" supported).

    Returns:
        List of LiteraryFinding objects; empty for non-EN languages.
    """
    if language != "EN":
        return []

    patterns = get_patterns(language)
    max_len  = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []
    reported_sents: Set[int] = set()

    for token in doc:
        # Locate "not" used as a negation particle
        if token.text.lower() != "not" or token.pos_ != "PART":
            continue

        # Find enclosing sentence for excerpt / position data
        sent = next((s for s in doc.sents if s.start <= token.i < s.end), None)
        if sent is None or sent.start in reported_sents:
            continue

        # Scan the next 1–3 tokens for an adjective / adverb
        adj_token = None
        confidence = 0.0
        for lookahead in doc[token.i + 1: min(token.i + 4, sent.end)]:
            if lookahead.pos_ not in ("ADJ", "ADV"):
                continue
            lemma = lookahead.lemma_.lower()

            if any(lemma.startswith(p) for p in _NEGATIVE_PREFIXES):
                # "not uncommon" → double negation = litotes
                adj_token  = lookahead
                confidence = 0.80
                break

            if lemma in _NEGATIVE_BASE_LEMMAS:
                # "not bad" → negating explicit negative = litotes
                adj_token  = lookahead
                confidence = 0.70
                break

        if adj_token is None:
            continue

        reported_sents.add(sent.start)
        char_start_abs = start_char + sent.start_char
        char_end_abs   = start_char + sent.end_char
        line_num       = char_to_line(char_start_abs, line_index)

        findings.append(LiteraryFinding(
            device="litotes",
            category="rhythmic",
            line_number=line_num,
            char_start=char_start_abs,
            char_end=char_end_abs,
            excerpt=_truncate(sent.text.strip(), max_len),
            matched_tokens=[token.text, adj_token.text],
            confidence=confidence,
            notes=(
                f'"not {adj_token.text}" — understatement via negation '
                f'of {"negative prefix" if confidence == 0.80 else "negative quality"}'
            ),
        ))

    return findings
