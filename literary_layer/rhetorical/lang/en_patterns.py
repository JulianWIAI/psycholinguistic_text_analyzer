"""
Literary Layer — English Language Patterns
Constant sets and compiled regex objects used by the EN rhetorical detectors.

All language-specific tuning lives here so the algorithm files (phonetic.py,
structural.py, semantic.py) stay language-agnostic and can be extended to DE/FR
by adding parallel pattern files and importing them in the detector.
"""
from __future__ import annotations

import re

# ── Vowel set (for initial-consonant extraction in alliteration) ───────────────
VOWELS: frozenset = frozenset("aeiouAEIOU")

# ── POS tags excluded from alliteration consonant-counting ────────────────────
# These pure function-word categories generate false positives when a common
# consonant letter happens to appear in many grammatical words.
# Example: "the thought that this…" — t appears in DET (the/this/that), which
# would incorrectly score as alliteration without this filter.
SKIP_POS_ALLITERATION: frozenset = frozenset({
    "DET",    # the, a, an, this, that, these, those
    "CCONJ",  # and, but, or, nor
    "SCONJ",  # because, although, if, while
    "PART",   # 's (possessive marker), to (infinitive marker)
})

# ── POS tags skipped when locating the first/last CONTENT token ───────────────
# Used by anaphora and epistrophe detectors to skip grammatical scaffolding and
# find the semantically meaningful word at the sentence boundary.
SKIP_POS_BOUNDARY: frozenset = frozenset({
    "DET",    # articles and demonstratives
    "PUNCT",  # punctuation tokens
    "SPACE",  # whitespace tokens
    "NUM",    # cardinal numbers
    "PART",   # particles
})

# ── Interrogative words that signal a genuine question ─────────────────────────
# Used by the rhetorical-question detector as a necessary (not sufficient)
# condition — the sentence must end with "?" AND contain one of these.
INTERROGATIVES: frozenset = frozenset({
    "who", "what", "why", "how", "when", "where", "which", "whom", "whose",
})

# ── Subjects that tip an interrogative toward rhetorical use ──────────────────
# Sentences addressed universally ("Can anyone…?") or philosophically ("Who
# among us…?") are more likely to be rhetorical than literal requests for info.
RHETORICAL_MARKERS: frozenset = frozenset({
    "anyone", "everyone", "nobody", "no", "one", "whoever",
    "whatever", "we", "you",
})

# ── Simile particles (Phase 5: used by language-aware simile detector) ────────
# "like" as ADP is the primary simile connector in English.
# The detector also checks pos_ == "ADP" so SIMILE_POS is not strictly needed
# for EN, but is defined here for interface symmetry with de/fr_patterns.
SIMILE_PARTICLES: frozenset = frozenset({"like"})
SIMILE_POS: frozenset = frozenset({"ADP"})

# ── "as … as" comparative simile (regex on raw sentence text) ─────────────────
# Matches "as [adjective/adverb phrase] as" regardless of spaCy's dep labeling
# of comparative "as", which varies across model versions.
# Group 1 captures the quality word(s) between the two "as" tokens.
AS_AS_RE: re.Pattern = re.compile(
    r"\bas\s+(\w+(?:\s+\w+)?)\s+as\b",
    re.IGNORECASE,
)

# ── Contrastive conjunctions used by antithesis detection (Phase 5) ───────────
# A sentence anchored by one of these with two substantial flanking clauses
# is a candidate for antithesis.
CONTRASTIVE_CONJ: frozenset = frozenset({
    "but", "yet", "whereas", "while", "however",
    "nevertheless", "although", "though", "conversely",
})

# ── Coordinating conjunctions for polysyndeton detection (Phase 6) ────────────
POLYSYNDETON_CONJ: frozenset = frozenset({"and", "or", "nor", "but", "yet"})

# ── Maximum excerpt length (chars) ────────────────────────────────────────────
# Excerpts are truncated at the last word boundary before this limit so the
# researcher always sees complete words in the evidence card.
EXCERPT_MAX: int = 140
