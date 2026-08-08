"""
Literary Layer — Figurative Rhetorical Devices (Phase 5)
Detects three devices that operate through figurative attribution or juxtaposition:

    Personification — an inanimate or abstract subject performs a human action.
                      Signal: nsubj dependency arc from a non-animate noun to a
                      verb whose lemma appears in a curated human-action set.

    Oxymoron        — two semantically opposite words placed in close proximity
                      (within the same sentence, within 5 token positions).
                      Detection uses a curated list of EN contradictory word pairs
                      compared against token lemmas.

    Antithesis      — two grammatically parallel clauses with contrasting content
                      joined by a contrastive conjunction (but / yet / whereas …).
                      Signal: contrastive CCONJ/SCONJ/ADV with ≥ 3 content words
                      on each side.

Phase 5: English only.
Phase 6 will extend with DE / FR human-action verbs and oxymoron pairs once
human-reviewed translation sets are available.
"""
from __future__ import annotations

import re
from typing import List, Set

from literary_layer.base import LiteraryFinding
from literary_layer.line_index import char_to_line
from literary_layer.rhetorical.lang import get_patterns


# ── Personification constants ──────────────────────────────────────────────────

# Lemmas of verbs that describe characteristically human actions.
# When an inanimate / abstract subject governs one of these verbs, the passage
# likely attributes human qualities to a non-human entity.
_HUMAN_VERBS_EN: frozenset = frozenset({
    "whisper", "speak", "talk", "call", "cry", "shout", "murmur",
    "moan", "groan", "sob", "laugh", "smile", "weep", "sigh",
    "sing", "dance", "walk", "run", "march",
    "think", "dream", "feel", "love", "hate", "fear", "desire",
    "remember", "forget", "mourn", "grieve", "yearn", "hunger",
    "breathe", "reach", "embrace", "stretch", "kneel", "bow", "beckon",
    "sleep", "wake", "watch", "listen", "see", "hear", "touch",
    "weave", "creep", "crawl", "stir", "rage", "brood",
})

# NER types that signal an animate subject — these are not personification.
# PERSON / PER covers named individuals; ORG is borderline but typically animate
# in the sense that organisations are treated as agents.
_ANIMATE_NER: frozenset = frozenset({"PERSON", "PER", "ORG"})

# POS tags for the content-word short-sentence filter (reused below)
_FUNCTION_POS: frozenset = frozenset({
    "DET", "ADP", "CCONJ", "SCONJ", "PART", "PUNCT", "SPACE",
})


# ── Oxymoron constants ─────────────────────────────────────────────────────────

# Curated list of contradictory English lemma pairs.
# Each tuple is (word_a, word_b); the detector checks whether BOTH lemmas
# appear in the same sentence within MAX_OXYMORON_SPAN token positions.
_EN_OXYMORON_PAIRS: List[tuple] = [
    ("bitter",      "sweet"),
    ("living",      "dead"),
    ("deafening",   "silence"),
    ("dark",        "light"),
    ("cold",        "fire"),
    ("cold",        "flame"),
    ("open",        "secret"),
    ("sweet",       "sorrow"),
    ("beautiful",   "disaster"),
    ("cruel",       "kindness"),
    ("friendly",    "fire"),
    ("controlled",  "chaos"),
    ("loud",        "silence"),
    ("silent",      "scream"),
    ("pretty",      "ugly"),
    ("alone",       "together"),
    ("love",        "hate"),
    ("old",         "new"),
    ("bright",      "darkness"),
    ("warm",        "cold"),
    ("peace",       "war"),
    ("true",        "false"),
    ("true",        "lie"),
    ("brave",       "coward"),
    ("joyful",      "sorrow"),
    ("clear",       "confused"),
    ("definite",    "maybe"),
    ("free",        "prison"),
    ("beginning",   "end"),
    ("rise",        "fall"),
    ("laugh",       "cry"),
    ("strength",    "weakness"),
    ("hope",        "despair"),
    ("light",       "shadow"),
]

# Maximum token distance between the two words of an oxymoron pair.
_MAX_OXYMORON_SPAN: int = 7


# ── Antithesis constants ───────────────────────────────────────────────────────

# Minimum content words required on each side of the contrastive conjunction.
_MIN_ANTITHESIS_SIDE: int = 3


# ── Private helpers ────────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int) -> str:
    """Cap *text* at *max_len* chars at the last word boundary."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rsplit(" ", 1)[0] + "…"


def _content_tokens(span, skip_pos: frozenset) -> list:
    """Return alpha tokens in *span* whose POS is not in *skip_pos*."""
    return [t for t in span if t.is_alpha and t.pos_ not in skip_pos]


# ── Personification ───────────────────────────────────────────────────────────

def detect_personification(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
) -> List[LiteraryFinding]:
    """
    Detect personification: an inanimate or abstract entity as the grammatical
    subject of a characteristically human action verb.

    Algorithm:
        1. Scan every token whose POS is VERB / AUX.
        2. Check whether its lemma is in the human-verb set.
        3. Find its nsubj (nominal subject) dependency child.
        4. The subject must NOT be: a personal pronoun, a known animate NER type
           (PERSON / PER), or an organisation (ORG).
        5. Remaining hits are reported as personification.

    Confidence 0.82 if the subject is a concrete noun (NOUN POS tag);
    0.65 if it is a proper noun or other category (more ambiguous).

    Currently English-only; the human-verb set is EN lemmas.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code (currently only "EN" is supported).

    Returns:
        List of LiteraryFinding objects; empty for non-EN languages.
    """
    # Human-verb detection relies on an EN lemma set — skip other languages.
    if language != "EN":
        return []

    patterns = get_patterns(language)
    max_len  = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []
    # Track sentences already reported to avoid duplicate findings per sentence
    reported_sents: Set[int] = set()

    for token in doc:
        if token.pos_ not in ("VERB", "AUX"):
            continue
        if token.lemma_.lower() not in _HUMAN_VERBS_EN:
            continue

        # Locate the nominal subject child
        subj = None
        for child in token.children:
            if child.dep_ == "nsubj" and child.is_alpha:
                subj = child
                break

        if subj is None:
            continue

        # Skip animate subjects: personal pronouns, named persons, organisations
        if subj.pos_ == "PRON":
            continue
        if subj.ent_type_ in _ANIMATE_NER:
            continue

        # Find the enclosing sentence for excerpt / position data
        sent = next((s for s in doc.sents if s.start <= token.i < s.end), None)
        if sent is None or sent.start in reported_sents:
            continue
        reported_sents.add(sent.start)

        char_start_abs = start_char + sent.start_char
        char_end_abs   = start_char + sent.end_char
        line_num       = char_to_line(char_start_abs, line_index)

        # Confidence depends on subject POS: NOUN is more clearly inanimate
        confidence = 0.82 if subj.pos_ == "NOUN" else 0.65

        findings.append(LiteraryFinding(
            device="personification",
            category="figurative",
            line_number=line_num,
            char_start=char_start_abs,
            char_end=char_end_abs,
            excerpt=_truncate(sent.text.strip(), max_len),
            matched_tokens=[subj.text, token.text],
            confidence=confidence,
            notes=(
                f'inanimate/abstract subject "{subj.text}" ({subj.pos_}) '
                f'governs human-action verb "{token.text}"'
            ),
        ))

    return findings


# ── Oxymoron ───────────────────────────────────────────────────────────────────

def detect_oxymoron(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
) -> List[LiteraryFinding]:
    """
    Detect oxymoron: two semantically opposite words placed within close
    token proximity (≤ _MAX_OXYMORON_SPAN positions) in the same sentence.

    Detection uses a curated lemma-pair list (_EN_OXYMORON_PAIRS).  Both
    words of a pair must appear in the sentence; the span between their
    positions must not exceed _MAX_OXYMORON_SPAN tokens.

    Each sentence is reported at most once per oxymoron pair, and at most one
    oxymoron finding is emitted per sentence (the first pair found wins).

    Currently English-only.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code (currently only "EN" is supported).

    Returns:
        List of LiteraryFinding objects; empty for non-EN languages.
    """
    if language != "EN":
        return []

    patterns = get_patterns(language)
    max_len  = patterns.EXCERPT_MAX

    findings: List[LiteraryFinding] = []

    for sent in doc.sents:
        # Build a map of lemma → list of token indices for fast lookup
        lemma_map: dict = {}
        for token in sent:
            if token.is_alpha:
                lemma_map.setdefault(token.lemma_.lower(), []).append(token)

        found_pair = None
        found_tokens = []

        # Check every oxymoron pair against this sentence's lemmas
        for (word_a, word_b) in _EN_OXYMORON_PAIRS:
            toks_a = lemma_map.get(word_a, [])
            toks_b = lemma_map.get(word_b, [])
            if not toks_a or not toks_b:
                continue

            # Find the closest pair of tokens (one from each word)
            for ta in toks_a:
                for tb in toks_b:
                    if abs(ta.i - tb.i) <= _MAX_OXYMORON_SPAN:
                        found_pair  = (word_a, word_b)
                        found_tokens = [ta, tb]
                        break
                if found_pair:
                    break
            if found_pair:
                break

        if not found_pair:
            continue

        char_start_abs = start_char + sent.start_char
        char_end_abs   = start_char + sent.end_char
        line_num       = char_to_line(char_start_abs, line_index)

        # Sort matched tokens by position so the excerpt highlight is left-to-right
        found_tokens.sort(key=lambda t: t.i)

        findings.append(LiteraryFinding(
            device="oxymoron",
            category="figurative",
            line_number=line_num,
            char_start=char_start_abs,
            char_end=char_end_abs,
            excerpt=_truncate(sent.text.strip(), max_len),
            matched_tokens=[t.text for t in found_tokens],
            confidence=0.85,
            notes=(
                f'contradictory pair: "{found_pair[0]}" ↔ "{found_pair[1]}" '
                f"within {abs(found_tokens[0].i - found_tokens[1].i)} token(s)"
            ),
        ))

    return findings


# ── Antithesis ─────────────────────────────────────────────────────────────────

def detect_antithesis(
    doc,
    start_char: int,
    line_index: List[int],
    language: str = "EN",
) -> List[LiteraryFinding]:
    """
    Detect antithesis: two grammatically parallel clauses with contrasting
    content, linked by a contrastive conjunction.

    Algorithm:
        1. Scan every sentence for a token whose lemma is in CONTRASTIVE_CONJ
           and whose POS is CCONJ, SCONJ, or ADV.
        2. Split the sentence at the conjunction into a left clause and a right
           clause.
        3. Both clauses must contain at least _MIN_ANTITHESIS_SIDE content words.
        4. Confidence is 0.80 for clear conjunctions (but / yet / whereas);
           0.65 for softer markers (although / however / while).

    Language-aware: CONTRASTIVE_CONJ is loaded from the language pattern module.

    Args:
        doc:         spaCy Doc for the current analysis window.
        start_char:  Absolute char offset of the window in the full document.
        line_index:  Pre-built char-to-line map from build_line_index().
        language:    ISO language code ("EN", "DE", "FR").

    Returns:
        List of LiteraryFinding objects.
    """
    patterns         = get_patterns(language)
    contrastive_conj = patterns.CONTRASTIVE_CONJ
    skip_pos         = patterns.SKIP_POS_BOUNDARY
    max_len          = patterns.EXCERPT_MAX

    # Conjunctions that merit higher confidence (unambiguously contrastive)
    _HIGH_CONF = frozenset({"but", "yet", "whereas", "aber", "sondern",
                            "wohingegen", "mais", "tandis"})

    findings: List[LiteraryFinding] = []
    reported: Set[int] = set()

    for sent in doc.sents:
        if sent.start in reported:
            continue

        # Locate the first contrastive conjunction in this sentence
        pivot = None
        for token in sent:
            if (token.lemma_.lower() in contrastive_conj
                    and token.pos_ in ("CCONJ", "SCONJ", "ADV")):
                pivot = token
                break

        if pivot is None:
            continue

        # Split at pivot: left = before it, right = after it (still inside sent)
        left_tokens  = _content_tokens(doc[sent.start:pivot.i],   skip_pos)
        right_tokens = _content_tokens(doc[pivot.i + 1:sent.end], skip_pos)

        if (len(left_tokens) < _MIN_ANTITHESIS_SIDE
                or len(right_tokens) < _MIN_ANTITHESIS_SIDE):
            continue

        reported.add(sent.start)
        char_start_abs = start_char + sent.start_char
        char_end_abs   = start_char + sent.end_char
        line_num       = char_to_line(char_start_abs, line_index)

        confidence = 0.80 if pivot.lemma_.lower() in _HIGH_CONF else 0.65

        findings.append(LiteraryFinding(
            device="antithesis",
            category="figurative",
            line_number=line_num,
            char_start=char_start_abs,
            char_end=char_end_abs,
            excerpt=_truncate(sent.text.strip(), max_len),
            matched_tokens=[left_tokens[-1].text, pivot.text, right_tokens[0].text],
            confidence=confidence,
            notes=(
                f'contrastive "{pivot.text}" ({pivot.pos_}) '
                f"splits {len(left_tokens)}-word clause from "
                f"{len(right_tokens)}-word clause"
            ),
        ))

    return findings
