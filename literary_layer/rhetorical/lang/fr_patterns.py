"""
Literary Layer — French Language Patterns (Phase 5)
Mirror of en_patterns.py for French.  All constants consumed by the shared
detector algorithms (phonetic.py, structural.py, semantic.py) so those files
stay language-agnostic; only the pattern values differ per language.

French-specific notes:
    • Vowels include accented letters (à, â, é, è, ê, ë, î, ï, ô, ù, û, ü,
      oe ligature œ, ae ligature æ) used in alliteration / assonance.
    • Simile particle is "comme" (like / as) — appears as SCONJ or ADP.
    • "aussi … que" is the French "as … as" comparative.
    • Interrogatives are the mots interrogatifs (qui, que, pourquoi, …).
"""
from __future__ import annotations

import re

# ── Vowel set including French accented vowels ────────────────────────────────
VOWELS: frozenset = frozenset(
    "aeiouàâéèêëîïôùûüœæyAEIOUÀÂÉÈÊËÎÏÔÙÛÜŒÆY"
)

# ── POS tags excluded from alliteration consonant groups ──────────────────────
SKIP_POS_ALLITERATION: frozenset = frozenset({
    "DET",    # le, la, les, un, une
    "CCONJ",  # et, ou, mais
    "SCONJ",  # que, si, comme
    "PART",   # particles
})

# ── POS tags skipped when locating sentence-boundary content tokens ───────────
SKIP_POS_BOUNDARY: frozenset = frozenset({
    "DET",
    "PUNCT",
    "SPACE",
    "NUM",
    "PART",
})

# ── French interrogative pronouns and adverbs ─────────────────────────────────
INTERROGATIVES: frozenset = frozenset({
    "qui",                              # who
    "que", "quoi",                      # what
    "pourquoi",                         # why
    "comment",                          # how
    "quand",                            # when
    "où",                               # where
    "lequel", "laquelle",               # which (masc./fem.)
    "lesquels", "lesquelles",           # which (plural)
    "quel", "quelle", "quels", "quelles",  # what/which (adjective)
    "combien",                          # how many / how much
})

# ── Rhetorical markers ────────────────────────────────────────────────────────
RHETORICAL_MARKERS: frozenset = frozenset({
    "tout", "tous", "toute", "toutes",  # all / everyone
    "chacun", "chacune",                # each / everyone
    "personne",                         # nobody (with ne)
    "nous",                             # we
    "on",                               # one / people (impersonal)
    "nul", "nulle",                     # none
    "aucun", "aucune",                  # no one
    "quiconque",                        # whoever (universal)
})

# ── Simile particles ───────────────────────────────────────────────────────────
# "comme" (like / as) is the primary simile connector in French.
SIMILE_PARTICLES: frozenset = frozenset({"comme"})
SIMILE_POS: frozenset = frozenset({"SCONJ", "ADP"})

# ── "aussi … que" comparative (French "as … as") ──────────────────────────────
# Captures the quality word(s) between "aussi" and "que".
# Example: "aussi courageux que un lion" → quality = "courageux"
AS_AS_RE: re.Pattern = re.compile(
    r"\baussi\s+(\w+(?:\s+\w+)?)\s+que\b",
    re.IGNORECASE,
)

# ── Contrastive conjunctions used by antithesis detection ─────────────────────
CONTRASTIVE_CONJ: frozenset = frozenset({
    "mais", "cependant", "pourtant", "néanmoins",
    "toutefois", "tandis", "whereas", "bien que",
})

# ── Coordinating conjunctions for polysyndeton detection ──────────────────────
POLYSYNDETON_CONJ: frozenset = frozenset({"et", "ou", "ni", "mais", "car"})

# ── Maximum excerpt length (chars) ────────────────────────────────────────────
EXCERPT_MAX: int = 140
