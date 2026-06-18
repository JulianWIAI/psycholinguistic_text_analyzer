"""
MODULE 2-FR — French Micro-Layer Override
Extends the Latin orthographic analyzer with French phonological rules.

Override applied to the positional multiplier:

    Silent Terminal Rule:
        If a French word ends in one of the canonical silent consonants
        (S, T, X, D — the most common word-final silent letters in French),
        the end-of-word positional multiplier is overridden from the
        standard 0.75 to 0.0.

        Rationale: the orthographic shape is present on the page but the
        phonosemantic echo is dead — it represents a psychological
        "trail-off" or hidden structural marker peculiar to French.
        This suppresses the terminal contribution of those letters,
        distinguishing written-French psychology from spoken-French.

All other BPV values, positional rules (start / middle), and interaction
coefficient logic remain identical to EN.
"""

from typing import Dict

from micro_layer.orthographic_analyzer import OrthographicAnalyzer, MicroScore
from micro_layer.base_analyzer import MicroResult


# Canonical silent terminal consonants in French
_FR_SILENT_TERMINALS = frozenset({"S", "T", "X", "D"})


class FrenchOrthographicAnalyzer(OrthographicAnalyzer):
    """
    French orthographic analyzer.
    Inherits the full Latin BPV pipeline; overrides only the
    end-of-word positional multiplier for silent terminal consonants.
    """

    @property
    def language_code(self) -> str:
        return "FR"

    # ------------------------------------------------------------------
    # Hook override: silent terminal rule
    # ------------------------------------------------------------------

    def _pos_mult(self, pos: int, last_idx: int, char: str) -> float:
        """
        For the final character of a word:
            • If it is a canonical French silent terminal → 0.0 (phonetic void)
            • Otherwise → standard multiplier (0.75)
        All other positions are unchanged.
        """
        if pos == last_idx and char in _FR_SILENT_TERMINALS:
            return 0.0
        return super()._pos_mult(pos, last_idx, char)

    # ------------------------------------------------------------------
    # Public interface: enrich raw output with French-specific audit data
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> MicroResult:
        score: MicroScore = self._score(text)

        # Track which words triggered the silent terminal suppression
        import re
        words = re.findall(r"[A-Za-z]+", text)
        silent_terminals_found = [
            {"word": w, "suppressed_char": w[-1]}
            for w in words
            if w and w[-1].upper() in _FR_SILENT_TERMINALS
        ]

        extra_raw = {
            "silent_terminal_count":   len(silent_terminals_found),
            "silent_terminals_found":  silent_terminals_found[:20],  # cap for response size
        }

        result = self._to_result(score, extra_raw)

        # Encode the "psychological trail-off" effect as a mild anxiety reduction
        # (silence where there should be sound → dampened anxiety vector)
        suppression_rate = len(silent_terminals_found) / max(1, len(words))
        result.vectors["anxiety"] = result.vectors.get("anxiety", 0.0) * (1.0 - suppression_rate * 0.3)

        return result
