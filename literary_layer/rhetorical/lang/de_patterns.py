"""
Literary Layer — German Language Patterns (Phase 5)
Mirror of en_patterns.py for German.  All constants consumed by the shared
detector algorithms (phonetic.py, structural.py, semantic.py) so those files
stay language-agnostic; only the pattern values differ per language.

German-specific notes:
    • Vowels include umlaut letters (ä, ö, ü) used in alliteration / assonance.
    • Simile particle is "wie" (fast/slow like …) — appears as SCONJ or ADP.
    • "so … wie" is the German "as … as" comparative.
    • Interrogatives are the W-Fragewörter (wer, was, warum, wie, …).
"""
from __future__ import annotations

import re

# ── Vowel set including German umlauts ────────────────────────────────────────
VOWELS: frozenset = frozenset("aeiouäöüyAEIOUÄÖÜY")

# ── POS tags excluded from alliteration consonant groups ──────────────────────
# Same functional word categories as EN; POS labels are model-independent.
SKIP_POS_ALLITERATION: frozenset = frozenset({
    "DET",    # der, die, das, ein, eine
    "CCONJ",  # und, aber, oder
    "SCONJ",  # weil, obwohl, dass
    "PART",   # nicht, zu (infinitive marker), ja, doch
})

# ── POS tags skipped when locating sentence-boundary content tokens ───────────
SKIP_POS_BOUNDARY: frozenset = frozenset({
    "DET",
    "PUNCT",
    "SPACE",
    "NUM",
    "PART",
})

# ── German W-Fragewörter (interrogative pronouns / adverbs) ───────────────────
# Used by the rhetorical-question detector as a necessary gate.
INTERROGATIVES: frozenset = frozenset({
    "wer", "wem", "wen", "wessen",            # who / whom / whose
    "was",                                      # what
    "warum", "weshalb", "weswegen", "wieso",   # why
    "wie", "wie viel", "wie viele",             # how / how much
    "wann",                                     # when
    "wo", "wohin", "woher", "wobei", "womit",  # where / whither / whence
    "welcher", "welche", "welches",            # which
    "inwieweit",                                # to what extent
})

# ── Rhetorical markers (universal / 2nd-person subjects) ──────────────────────
# Elevate a question toward rhetorical use when present.
RHETORICAL_MARKERS: frozenset = frozenset({
    "jeder", "jede", "jedes",      # everyone / every
    "jemand",                       # someone
    "niemand",                      # nobody
    "alle", "alles",                # all / everything
    "keiner", "keine", "keines",   # none
    "wir",                          # we
    "man",                          # one / people (impersonal)
    "irgendwer", "irgendwas",      # anyone / anything (rhetorical universals)
})

# ── Simile particles ───────────────────────────────────────────────────────────
# "wie" (as/like) is the primary simile connector in German.
# Accepted POS tags vary across model versions (SCONJ or ADP or ADV).
SIMILE_PARTICLES: frozenset = frozenset({"wie"})
SIMILE_POS: frozenset = frozenset({"SCONJ", "ADP", "ADV"})

# ── "so … wie" comparative (German "as … as") ─────────────────────────────────
# Captures the quality word(s) between "so" and "wie".
# Example: "so schnell wie ein Pfeil" → quality = "schnell"
AS_AS_RE: re.Pattern = re.compile(
    r"\bso\s+(\w+(?:\s+\w+)?)\s+wie\b",
    re.IGNORECASE,
)

# ── Contrastive conjunctions used by antithesis detection ─────────────────────
CONTRASTIVE_CONJ: frozenset = frozenset({
    "aber", "jedoch", "doch", "sondern",
    "obwohl", "während", "wohingegen",
})

# ── Coordinating conjunctions for polysyndeton detection ──────────────────────
POLYSYNDETON_CONJ: frozenset = frozenset({"und", "oder", "noch", "aber", "denn"})

# ── Maximum excerpt length (chars) ────────────────────────────────────────────
EXCERPT_MAX: int = 140
