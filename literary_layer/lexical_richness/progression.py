"""
Literary Layer — Lexical Richness Progression Analyzer (Phase 9)
Computes a moving-average TTR waveform over the analysis window, revealing
where the author's vocabulary diversifies or collapses.

The primary output — mattr_curve — is a 10-point MATTR waveform sampled at
evenly spaced sub-window positions.  Each value is the Moving-Average TTR
(window=50 tokens) of the content tokens centred at that position.  Plotting
these 10 values gives the researcher a richness "fingerprint waveform":

    • A rising curve → vocabulary grows richer toward the end of the passage
      (common in building arguments or narrative climax).
    • A falling curve → vocabulary contracts (repetition, semantic field
      narrowing, creative fatigue, or deliberate stylistic choice).
    • A spike followed by collapse → register shift, vocabulary injection
      (e.g. quotation, scene change, shift from narration to exposition).
    • Flat curve → highly controlled register with consistent vocabulary.

Additional diagnostics:
    hapax_ratio         — vocabulary uniqueness (high → diverse, inventive)
    vocab_growth_ratio  — actual unique words vs. Heaps' law prediction;
                          ratio > 1 means richer than expected for the text length
    richness_label      — "rich" / "moderate" / "sparse" from overall MATTR
    register_shift      — True when max−min of mattr_curve exceeds 0.25

Language note: mattr_curve is computed on lemmatised, stop-word-filtered content
tokens so the measurement is language-agnostic and comparable across EN/DE/FR.
"""
from __future__ import annotations

import math
from typing import List

from literary_layer.base import LexicalProgressionResult
from literary_layer.narrative.readability import compute_mattr

# ── Curve sampling parameters ──────────────────────────────────────────────────
_N_POINTS:    int   = 10    # number of MATTR sample points along the waveform
_MATTR_WIN:   int   = 50    # sliding-window size inside each sample (tokens)

# ── Heaps' law constants (calibrated for general English/German/French prose) ──
# Heaps' law: V(n) ≈ K × n^β   (V = unique types, n = total tokens)
# K=10, β=0.5 gives a reasonable baseline for 100–2000-token windows.
_HEAPS_K:    float  = 10.0
_HEAPS_BETA: float  = 0.50

# ── Richness thresholds (MATTR-based) ─────────────────────────────────────────
_RICH_THRESHOLD:     float = 0.75
_MODERATE_THRESHOLD: float = 0.50

# ── Register-shift detection ───────────────────────────────────────────────────
_SHIFT_THRESHOLD: float = 0.25   # max − min MATTR swing to flag a register shift


class LexicalRichnessAnalyzer:
    """
    Stateless lexical richness analyzer.

    Instantiate once as a singleton in LiteraryAnalyzer.__init__() and reuse
    across all windows — the analyzer carries no per-document state.

    Usage:
        analyzer = LexicalRichnessAnalyzer()
        result   = analyzer.analyze(doc)
    """

    def analyze(self, doc) -> LexicalProgressionResult:
        """
        Compute the lexical richness profile for *doc*.

        Args:
            doc:  Pre-parsed spaCy Doc for the analysis window.

        Returns:
            LexicalProgressionResult with waveform, diagnostics, and labels.
        """
        # Extract lemmatised content tokens (non-stop, alpha, length > 1)
        # Using lemmas removes inflection noise so "run"/"ran"/"runs" = 1 type.
        content_tokens: List[str] = [
            t.lemma_.lower()
            for t in doc
            if t.is_alpha and not t.is_stop and len(t.text) > 1
        ]

        if len(content_tokens) < 10:
            # Too short to produce a meaningful curve
            return LexicalProgressionResult(
                mattr_curve        = [],
                mattr_trend        = "stable",
                hapax_ratio        = 0.0,
                vocab_growth_ratio = 0.0,
                richness_label     = "sparse",
                register_shift     = False,
            )

        # ── MATTR waveform ─────────────────────────────────────────────────────
        mattr_curve = self._mattr_curve(content_tokens)

        # ── Hapax ratio ────────────────────────────────────────────────────────
        hapax_ratio = self._hapax_ratio(content_tokens)

        # ── Vocabulary growth vs. Heaps' law ──────────────────────────────────
        vocab_growth_ratio = self._vocab_growth_ratio(content_tokens)

        # ── Overall richness label from full-window MATTR ─────────────────────
        overall_mattr     = compute_mattr(content_tokens)
        richness_label    = self._richness_label(overall_mattr)

        # ── Register-shift detection ───────────────────────────────────────────
        register_shift = (
            len(mattr_curve) >= 3
            and (max(mattr_curve) - min(mattr_curve)) > _SHIFT_THRESHOLD
        )

        # ── Trend: compare first-half average to second-half average ──────────
        mattr_trend = self._mattr_trend(mattr_curve)

        return LexicalProgressionResult(
            mattr_curve        = mattr_curve,
            mattr_trend        = mattr_trend,
            hapax_ratio        = round(hapax_ratio,        3),
            vocab_growth_ratio = round(vocab_growth_ratio, 3),
            richness_label     = richness_label,
            register_shift     = register_shift,
        )

    # ── Private methods ────────────────────────────────────────────────────────

    def _mattr_curve(self, tokens: List[str]) -> List[float]:
        """
        Sample MATTR at _N_POINTS evenly spaced positions across *tokens*.

        At each sample point i, take the slice of _MATTR_WIN tokens centred
        at that position and compute its TTR.  For positions near the start or
        end where a full centred window is not possible, the window is clamped
        to the available tokens (no zero-padding).

        Returns a list of _N_POINTS float values in [0, 1].
        """
        n = len(tokens)
        half = _MATTR_WIN // 2
        curve: List[float] = []

        for i in range(_N_POINTS):
            # Map sample index to token index (0 → first token, N-1 → last)
            centre = int(i / (_N_POINTS - 1) * (n - 1)) if _N_POINTS > 1 else n // 2
            lo = max(0, centre - half)
            hi = min(n, centre + half)
            window = tokens[lo:hi]
            if not window:
                curve.append(0.0)
                continue
            ttr = len(set(window)) / len(window)
            curve.append(round(ttr, 3))

        return curve

    def _hapax_ratio(self, tokens: List[str]) -> float:
        """
        Compute hapax legomena ratio: word types appearing exactly once /
        total unique word types.
        """
        freq: dict = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1

        unique = len(freq)
        hapax  = sum(1 for c in freq.values() if c == 1)
        return hapax / max(1, unique)

    def _vocab_growth_ratio(self, tokens: List[str]) -> float:
        """
        Compare actual unique types to the Heaps' law prediction.

        Heaps' law:  V_predicted = K × n^β
        Ratio = V_actual / V_predicted
            > 1  → vocabulary is richer than the length would predict
            = 1  → exactly as expected
            < 1  → vocabulary is sparser than expected (repetition / narrow domain)
        """
        n          = len(tokens)
        v_actual   = len(set(tokens))
        v_predicted = _HEAPS_K * (n ** _HEAPS_BETA)
        return v_actual / max(1.0, v_predicted)

    def _richness_label(self, mattr: float) -> str:
        """Map overall MATTR to a human-readable richness tier."""
        if mattr >= _RICH_THRESHOLD:
            return "rich"
        if mattr >= _MODERATE_THRESHOLD:
            return "moderate"
        return "sparse"

    def _mattr_trend(self, curve: List[float]) -> str:
        """
        Determine whether lexical richness is increasing, decreasing, or stable
        across the window by comparing the mean of the first half to the mean
        of the second half of the MATTR curve.

        Returns "increasing", "decreasing", or "stable".
        """
        if len(curve) < 4:
            return "stable"

        mid         = len(curve) // 2
        first_half  = sum(curve[:mid])  / mid
        second_half = sum(curve[mid:])  / len(curve[mid:])
        delta       = second_half - first_half

        if delta > 0.05:
            return "increasing"
        if delta < -0.05:
            return "decreasing"
        return "stable"
