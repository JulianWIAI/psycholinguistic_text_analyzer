"""
lexicon_layer/token_cleanser.py
═══════════════════════════════════════════════════════════════════
Token Validation & Normalisation for Lexicon Ingestion
═══════════════════════════════════════════════════════════════════

Single-responsibility class that decides whether a raw string from a
lexicon file is suitable for use as a single-token lookup key in the
spaCy-powered analysis pipeline.

Why this matters
────────────────
The spaCy tokeniser produces individual surface/lemma tokens.  If a
lexicon key is a multi-word phrase ("أداة عمل", "work tool") it will
never match any single token and wastes memory.  If it is punctuation-
heavy ("---", ">>!") it introduces false-positive zero-score lookups.
Filtering these at ingest time — once, at load — keeps the in-memory
dictionaries small and every downstream lookup O(1) with no waste.

Three-gate rejection pipeline
──────────────────────────────
Gate 1 — Empty / blank strings:
    Raw cell is empty or becomes empty after strip().

Gate 2 — N-gram detector:
    The cleaned token contains any Unicode whitespace character.
    A space means spaCy would never produce this as a single token.
    Examples rejected: "أداة عمل", "work tool", "la maison".

Gate 3 — Noise / punctuation-heavy detector:
    Uses `[^\\W_]` (Unicode letters and digits, excluding underscore)
    as the definition of a "word character".  If the ratio of word
    characters to total characters is below MIN_WORD_CHAR_RATIO (0.5),
    the token is considered noise.
    Examples rejected:  "---",  "!!",  ">>",  "…—…"
    Examples accepted:  "hello", "слово", "안녕", "abc-def" (3/7 ≈ 0.43 → rejected),
                        "don't" (4/5 = 0.8 → accepted).

Note on underscore: `\\W` in Python's `re` module considers `_` a word
character.  This module explicitly EXCLUDES it via `[^\\W_]` so that
strings like "___" (zero alphanumeric chars) are correctly rejected as
noise, while strings like "can't" are correctly accepted (word chars:
c,a,n,t = 4 out of 5 = 0.8 ≥ 0.5).

Public interface
────────────────
    cleanser = TokenCleanser()
    key = cleanser.cleanse(raw_string)   # str | None
    if key is None:
        # skip this row

Thread safety
─────────────
TokenCleanser holds no mutable state — all compiled patterns and
thresholds are class-level constants.  Instances are safe to share
across threads without locking.
"""

from __future__ import annotations

import re
from typing import Optional


class TokenCleanser:
    """
    Validates and normalises a raw lexicon cell into a single-token key.

    All filtering logic is encapsulated here so that both
    LexiconIngestionEngine.load_intensity_lexicon() and
    LexiconIngestionEngine.load_ousiometric_lexicon() share the exact
    same rejection rules without code duplication.
    """

    # ── Gate 2: n-gram detector ───────────────────────────────────────────
    # Matches any Unicode whitespace (space, tab, non-breaking space, etc.)
    # Compiled once at class definition time — zero cost per call.
    _WHITESPACE_RE: re.Pattern = re.compile(r'\s', re.UNICODE)

    # ── Gate 3: word-character counter ───────────────────────────────────
    # [^\W_]  =  NOT (non-word OR underscore)
    #         =  Unicode letters and decimal digits only.
    # `\W` matches anything that is NOT [a-zA-Z0-9_], so `[^\W_]` matches
    # Unicode letters/digits across all scripts: Latin, Cyrillic, Arabic,
    # Hangul, CJK, etc.
    _WORD_CHAR_RE: re.Pattern = re.compile(r'[^\W_]', re.UNICODE)

    # Minimum ratio of word characters to total characters.
    # A value of 0.5 means at least half the characters in the token
    # must be letters or digits.  Anything below this is considered noise.
    MIN_WORD_CHAR_RATIO: float = 0.5

    # ── Public API ────────────────────────────────────────────────────────

    def cleanse(self, raw_token: str) -> Optional[str]:
        """
        Normalise *raw_token* and validate it as a single-token key.

        Parameters
        ----------
        raw_token : str
            The raw cell value extracted from a lexicon file column
            (e.g. Column 3 of an intensity file or Column 4 of a VAD file).

        Returns
        -------
        str | None
            The cleaned, lowercased token if it passes all three gates.
            None if the token should be rejected — the caller must skip
            the entire lexicon row in this case.

        Processing steps (applied in order)
        ────────────────────────────────────
        1. Strip leading/trailing whitespace.
        2. Gate 1: reject empty strings.
        3. Lowercase (normalises lookup surface).
        4. Gate 2: reject if internal whitespace remains (n-gram).
        5. Gate 3: reject if word-char ratio < MIN_WORD_CHAR_RATIO.
        6. Return the valid token.
        """
        # ── Step 1: strip surrounding whitespace ──────────────────────────
        token: str = raw_token.strip()

        # ── Gate 1: empty string ─────────────────────────────────────────
        if not token:
            return None

        # ── Step 3: lowercase ─────────────────────────────────────────────
        # Applied before Gate 2 so that any whitespace normalisation by
        # .lower() does not skip the space check (Python's .lower() on
        # ASCII whitespace returns the same character unchanged).
        token = token.lower()

        # ── Gate 2: n-gram detector ───────────────────────────────────────
        # A token with internal whitespace (e.g. "أداة عمل") is a phrase,
        # not a single token, and will never match a spaCy lemma.
        if self._WHITESPACE_RE.search(token):
            return None

        # ── Gate 3: noise / punctuation-heavy detector ────────────────────
        word_chars: list = self._WORD_CHAR_RE.findall(token)

        # Must contain at least one letter or digit in any Unicode script.
        if not word_chars:
            return None

        # Reject if punctuation/symbols outnumber letters/digits.
        if len(word_chars) / len(token) < self.MIN_WORD_CHAR_RATIO:
            return None

        return token

    # ── Diagnostic helpers ────────────────────────────────────────────────
    # These are not used in the hot path but are useful for unit tests
    # and deployment audits.

    def is_ngram(self, token: str) -> bool:
        """Return True if *token* contains any internal whitespace."""
        return bool(self._WHITESPACE_RE.search(token))

    def word_char_ratio(self, token: str) -> float:
        """
        Return the ratio of word characters to total characters in *token*.

        A ratio below MIN_WORD_CHAR_RATIO causes Gate 3 to reject the token.
        Returns 0.0 for the empty string.
        """
        if not token:
            return 0.0
        return len(self._WORD_CHAR_RE.findall(token)) / len(token)
