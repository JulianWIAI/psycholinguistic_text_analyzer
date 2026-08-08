"""
Literary Layer — English Argumentation Patterns (Phase 7)
Trigger word sets and phrase lists for Ethos / Pathos / Logos classification
and for claim / premise / evidence function detection.

Design principle: each set focuses on high-precision signals rather than high
recall — it is better to miss a weak instance than to flood the researcher
with false positives.  Phrase matches (multi-word strings) score 2 points;
single-word matches score 1 point.  A sentence is classified only when its
dominant appeal score reaches MIN_SCORE.
"""
from __future__ import annotations
from typing import List

# ── Minimum score for a sentence to be classified ─────────────────────────────
MIN_SCORE: int = 2

# ══════════════════════════════════════════════════════════════════════════════
# LOGOS — rational / evidential appeal
# ══════════════════════════════════════════════════════════════════════════════

# Single-word logical connectors that signal deductive or causal reasoning.
# "so" is excluded as it is too ambiguous in isolation.
LOGOS_CONNECTORS: frozenset = frozenset({
    "therefore", "thus", "hence", "consequently", "accordingly",
    "ergo", "thereby",
})

# Single-word evidence or empirical reference markers.
LOGOS_EVIDENCE_WORDS: frozenset = frozenset({
    "evidence", "data", "statistics", "study", "studies", "research",
    "survey", "experiment", "analysis", "findings", "results", "proof",
    "measurement", "observation", "report", "figure", "percentage",
})

# Causal and conditional verbs that signal logical structure.
LOGOS_CAUSAL_VERBS: frozenset = frozenset({
    "demonstrates", "demonstrates", "shows", "proves", "confirms",
    "indicates", "suggests", "reveals", "supports", "verifies",
    "implies", "entails", "follows",
})

# Multi-word phrases that strongly signal evidence-based reasoning (2 pts each).
LOGOS_PHRASES: List[str] = [
    "for example", "for instance", "such as",
    "as shown by", "as demonstrated by", "as evidenced by",
    "as illustrated by", "according to the data",
    "data shows", "data suggest", "research shows", "research indicates",
    "studies show", "studies indicate", "statistics show",
    "the evidence suggests", "it follows that", "we can conclude",
    "this proves", "this demonstrates", "this shows",
    "in conclusion", "to summarise", "to summarize",
    "if … then", "because of this", "as a result",
    "for this reason", "on the basis of",
]

# ══════════════════════════════════════════════════════════════════════════════
# ETHOS — credibility / authority appeal
# ══════════════════════════════════════════════════════════════════════════════

# Single-word authority or credibility markers.
ETHOS_AUTHORITY_WORDS: frozenset = frozenset({
    "expert", "experts", "scientist", "scientists",
    "researcher", "researchers", "scholar", "scholars",
    "professor", "authority", "authorities", "specialist",
    "professional", "professionals", "literature", "journal",
    "published", "peer-reviewed", "consensus", "established",
    "verified", "confirmed", "proven", "trusted", "credible",
    "reliable", "citation", "reference",
})

# Multi-word phrases signalling appeal to authority or source credibility (2 pts).
ETHOS_PHRASES: List[str] = [
    "according to", "as stated by", "as noted by",
    "as shown by experts", "experts agree", "experts say",
    "research shows", "scholars have found", "it is well established",
    "it is widely accepted", "as widely accepted",
    "in my experience", "as a professional", "in the field",
    "peer-reviewed research", "published studies",
    "the scientific consensus", "authoritative sources",
]

# ══════════════════════════════════════════════════════════════════════════════
# PATHOS — emotional / motivational appeal
# ══════════════════════════════════════════════════════════════════════════════

# Single-word emotion vocabulary that signals affective appeal.
PATHOS_EMOTION_WORDS: frozenset = frozenset({
    "love", "fear", "hope", "joy", "pain", "sorrow", "grief",
    "pride", "shame", "anger", "despair", "happiness", "sadness",
    "terror", "compassion", "empathy", "suffering", "sacrifice",
    "dignity", "justice", "freedom", "oppression", "innocent",
    "victim", "children", "family", "community", "humanity",
    "heart", "soul", "courage", "bravery", "tragedy", "outrage",
    "injustice", "cruelty", "mercy", "pity", "horror", "beloved",
    "cherish", "mourn", "weep", "cry", "laugh",
})

# High-intensity adverbs and adjectives that amplify emotional register.
PATHOS_INTENSIFIERS: frozenset = frozenset({
    "deeply", "profoundly", "utterly", "desperately", "passionately",
    "heartbreaking", "devastating", "wonderful", "terrible", "horrifying",
    "beautiful", "tragic", "inspiring", "moving", "touching", "unbearable",
    "overwhelming", "extraordinary", "shocking", "alarming", "urgent",
})

# Multi-word emotional appeal phrases (2 pts each).
PATHOS_PHRASES: List[str] = [
    "think of the children", "our children", "our families",
    "for the sake of", "we cannot stand by", "we must act",
    "imagine the suffering", "consider the pain",
    "the human cost", "lives are at stake", "people are dying",
    "no one should", "nobody deserves", "everyone deserves",
    "at the heart of", "deeply moving", "profoundly disturbing",
]

# ══════════════════════════════════════════════════════════════════════════════
# ARGUMENTATIVE FUNCTION detection
# ══════════════════════════════════════════════════════════════════════════════

# Verbs whose subject is asserting a position — claim function signal.
CLAIM_VERBS: frozenset = frozenset({
    "argue", "claim", "assert", "maintain", "contend",
    "propose", "believe", "insist", "posit", "state",
    "hold", "submit", "advance",
})

# Words and phrases that mark a claim opener (check at sentence start).
CLAIM_OPENERS: List[str] = [
    "i believe", "i argue", "i contend", "i maintain", "i propose",
    "we believe", "we argue", "we contend", "one must",
    "it is clear", "it is obvious", "it is evident", "it must be",
    "clearly", "obviously", "undoubtedly", "certainly", "without doubt",
    "it is beyond question", "there is no doubt",
]

# Words that mark a supportive premise (reason/because structure).
PREMISE_MARKERS: frozenset = frozenset({
    "because", "since", "given", "considering",
    "seeing", "provided", "assuming", "inasmuch",
})

PREMISE_PHRASES: List[str] = [
    "for the reason that", "given that", "in light of",
    "on the grounds that", "owing to", "due to",
    "in view of", "based on", "taking into account",
    "as a consequence of",
]

# Words that introduce concrete evidence.
EVIDENCE_PHRASES: List[str] = [
    "for example", "for instance", "as shown by",
    "according to", "data shows", "research shows",
    "studies indicate", "statistics show", "the figures show",
    "in the case of", "as illustrated by", "such as",
    "a case in point", "to illustrate",
]
