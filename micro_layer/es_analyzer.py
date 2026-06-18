"""
MODULE 2-ES — Spanish Micro-Layer Override
Extends the Latin orthographic analyzer with Spanish phonosemantic rules.

Overrides applied before the standard BPV math:

    RR  — Treated as a distinct phonetic entity (vibrante multiple).
          Applies an extreme Agitation/Motion multiplier: base R score × 2.0.
          (vs. the default Liquid/Nasal gm of 1.4)

    LL  — Treated as a fluid/sinuous phonetic entity (lateral palatal).
          Applies a Fluidity/Sinuosity multiplier: base L score × 1.5.
          (vs. the default Liquid/Nasal gm of 1.4)

All other phonosemantic and positional rules remain identical to EN.
"""

from typing import Dict

from micro_layer.orthographic_analyzer import OrthographicAnalyzer, MicroScore
from micro_layer.base_analyzer import MicroResult


# Spanish-specific geometric multipliers for the two overridden digraphs
_ES_DOUBLE_GM: Dict[str, float] = {
    "R": 2.0,   # RR → extreme Agitation/Motion
    "L": 1.5,   # LL → Fluidity/Sinuosity
}


class SpanishOrthographicAnalyzer(OrthographicAnalyzer):
    """
    Spanish orthographic analyzer.
    Inherits the full Latin BPV pipeline; overrides only the two
    canonical Spanish double-consonant digraphs (RR, LL).
    """

    @property
    def language_code(self) -> str:
        return "ES"

    # ------------------------------------------------------------------
    # Hook override: Spanish phonosemantic multipliers
    # ------------------------------------------------------------------

    def _double_gm(self, letter: str) -> float:
        """
        Intercept RR and LL before the standard phonosemantic table.
        All other doubles fall through to the default Latin rules.
        """
        if letter in _ES_DOUBLE_GM:
            return _ES_DOUBLE_GM[letter]
        return super()._double_gm(letter)

    # ------------------------------------------------------------------
    # Public interface: enrich raw output with Spanish-specific events
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> MicroResult:
        score: MicroScore = self._score(text)

        # Extract RR and LL specific events for the raw audit trail
        rr_events = [
            {"word": e.word, "gm": e.gm, "score": round(e.score, 4)}
            for e in score.double_letter_events if e.pair == "RR"
        ]
        ll_events = [
            {"word": e.word, "gm": e.gm, "score": round(e.score, 4)}
            for e in score.double_letter_events if e.pair == "LL"
        ]

        extra_raw = {
            "rr_events": rr_events,
            "ll_events": ll_events,
            "rr_count":  len(rr_events),
            "ll_count":  len(ll_events),
        }

        result = self._to_result(score, extra_raw)

        # Boost agitation vector proportionally to RR density
        # (already reflected in raw_score; this makes it explicit in the vector)
        if rr_events:
            rr_boost = sum(e["score"] for e in rr_events)
            result.vectors["agitation"] = result.vectors.get("agitation", 0.0) + rr_boost / max(1.0, score.raw_score) * 100

        return result
