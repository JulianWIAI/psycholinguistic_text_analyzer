"""
Literary Layer — English Function Word List (Phase 8)
The top ~50 English function words used as the basis for the Burrows' Delta
stylometric fingerprint.  These are the most frequent grammatical words in
English prose; their per-text frequency profiles form an author's fingerprint.

Reference: Burrows (2002) 'Delta': a Measure of Stylistic Difference and a
Guide to Likely Authorship in Ill-Attributed Works.  Literary and Linguistic
Computing 17(3):267-287.
"""
from __future__ import annotations
from typing import List

# ── Core function word list ────────────────────────────────────────────────────
# Ordered roughly by corpus frequency (BNC / COCA); all lowercase.
# Do NOT add content words here — function words only.
FUNCTION_WORDS: List[str] = [
    "the", "and", "of", "to", "a", "in", "that", "is", "it",
    "as", "was", "for", "on", "are", "with", "his", "he", "be",
    "this", "from", "or", "had", "by", "but", "not", "she",
    "they", "were", "we", "been", "have", "has", "an", "do",
    "does", "did", "would", "could", "should", "will", "can",
    "may", "might", "must", "shall", "their", "there", "its",
    "all", "which", "when", "who", "what", "if", "then", "than",
    "so", "at", "him", "her", "them", "our", "my", "your",
    "me", "us", "one", "no", "nor", "yet", "both", "neither",
    "each", "any", "some", "such", "these", "those", "also",
    "very", "just", "more", "most", "only", "even", "into",
]
