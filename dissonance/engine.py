"""
MODULE 4 — Statistical Baselines & The Dissonance Engine

Does not use raw scores — evaluates targets against statistical variance
from their own baseline.

Pipeline:
    1. Baseline Tracking  — running μ (mean) and σ (std dev) per variable
    2. Z-Score            — Z = (X - μ) / σ
    3. EMA                — EMA_new = X_new * α + EMA_prev * (1 - α)
    4. Dissonance Trigger — Δ = |Z_macro - Z_micro|; if Δ > threshold → event
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Tuple

# Defaults
DEFAULT_ALPHA: float = 0.1
DEFAULT_THRESHOLD: float = 2.5


# ---------------------------------------------------------------------------
# Baseline statistics tracker (Welford-style online update)
# ---------------------------------------------------------------------------

@dataclass
class BaselineStats:
    """
    Maintains running mean, standard deviation, and EMA for a single variable.
    Uses numerically stable incremental formulas.
    """
    n: int = 0
    mu: float = 0.0          # running mean
    sigma: float = 1.0       # running std dev (seeded to 1 to avoid division by zero)
    ema: float = 0.0         # exponential moving average
    _M2: float = 0.0         # sum of squared deviations (Welford)

    def update(self, value: float, alpha: float = DEFAULT_ALPHA) -> None:
        """Ingest a new observation and update all statistics."""
        self.n += 1
        # Welford's online algorithm for mean and variance
        delta = value - self.mu
        self.mu += delta / self.n
        delta2 = value - self.mu
        self._M2 += delta * delta2
        if self.n > 1:
            variance = self._M2 / (self.n - 1)
            self.sigma = math.sqrt(max(variance, 1e-9))
        # EMA update
        self.ema = (value * alpha) + (self.ema * (1.0 - alpha))

    def z_score(self, value: float) -> float:
        """Return Z-score of *value* against the current baseline.

        Task 2 guard: when n < 2 the engine has no variance history
        (update() was just called with this value, so mu == value and the
        standard formula always returns 0).  In that case, return the raw
        value so a non-zero score produces a visible signal on the first
        observation rather than being silently swallowed.
        """
        if self.n < 2:
            return value
        return (value - self.mu) / self.sigma if self.sigma > 0 else 0.0

    def to_dict(self) -> dict:
        return {"mu": self.mu, "sigma": self.sigma, "ema": self.ema, "n": self.n}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DissonanceEvent:
    event_id: str
    timestamp: str
    source_document_id: str
    trigger_type: str
    vectors_involved: List[str]
    delta_score: float
    algorithmic_conclusion: str

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source_document_id": self.source_document_id,
            "trigger_type": self.trigger_type,
            "vectors_involved": self.vectors_involved,
            "delta_score": self.delta_score,
            "algorithmic_conclusion": self.algorithmic_conclusion,
        }


@dataclass
class WindowAnalysisResult:
    z_scores_micro: Dict[str, float] = field(default_factory=dict)
    z_scores_macro: Dict[str, float] = field(default_factory=dict)
    ema_snapshot: Dict[str, float] = field(default_factory=dict)
    dissonance_events: List[DissonanceEvent] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Semantic bridge: which micro variable pairs with which macro variable
# ---------------------------------------------------------------------------

# Maps micro_key -> macro_key for the Δ comparison.
# Uses the standardized six-vector space so all languages resolve to the same pairs.
# EN/ES/FR: intensity/anxiety/attention/emotion/agitation/complexity from BPV pipeline.
# JA:       intensity=kanji_ratio, emotion=hiragana_ratio, agitation=katakana_ratio,
#           complexity=stroke_density; keigo_formal maps to power_submission.
_COMPARISON_BRIDGE: List[Tuple[str, str]] = [
    ("intensity",   "power_control"),           # orthographic pressure ↔ power vocab
    ("anxiety",     "power_submission"),         # nervousness ↔ submission framing
    ("attention",   "visibility_exposure"),      # ego/focus ↔ exposure framing
    ("emotion",     "resources_abundance"),      # emotional load ↔ abundance framing
    ("agitation",   "power_control"),            # restlessness ↔ control assertion
    ("complexity",  "visibility_concealment"),   # logographic weight ↔ concealment vocab
    ("attention",   "cognitive_scientific"),     # focused attention ↔ empirical framing
    ("agitation",   "kinetic_aggression"),       # restlessness ↔ aggression framing
    ("emotion",     "cognitive_emotional"),      # emotional load ↔ abstract framing
    ("anxiety",     "kinetic_aggression"),       # threat anxiety ↔ hostile intent
    # Japanese Keigo-specific bridge
    ("intensity",   "keigo_formal"),             # kanji density ↔ formal register distance
]


# ---------------------------------------------------------------------------
# Dissonance Engine
# ---------------------------------------------------------------------------

class DissonanceEngine:
    """
    Central engine that:
        • maintains per-variable baseline statistics
        • converts raw observations to Z-scores
        • tracks EMA drift
        • detects and classifies dissonance events
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.alpha = alpha
        self.threshold = threshold
        self.micro_baselines: Dict[str, BaselineStats] = {}
        self.macro_baselines: Dict[str, BaselineStats] = {}

    # ------------------------------------------------------------------
    # Baseline seeding (call once with a control/reference corpus)
    # ------------------------------------------------------------------

    def seed_baselines(
        self,
        micro_observations: Dict[str, float],
        macro_observations: Dict[str, float],
    ) -> None:
        """Seed initial baselines from a representative control text."""
        for key, val in micro_observations.items():
            self._update_micro(key, val)
        for key, val in macro_observations.items():
            self._update_macro(key, val)

    # ------------------------------------------------------------------
    # Per-window analysis
    # ------------------------------------------------------------------

    def analyze_window(
        self,
        micro_scores: Dict[str, float],
        macro_scores: Dict[str, float],
        document_id: str = "unknown",
    ) -> WindowAnalysisResult:
        """
        Process one window:
            1. Update baselines with new observations
            2. Compute Z-scores
            3. Detect dissonance pairs that exceed threshold Δ
        """
        # Update baselines with this window's values
        for key, val in micro_scores.items():
            self._update_micro(key, val)
        for key, val in macro_scores.items():
            self._update_macro(key, val)

        # Compute Z-scores
        z_micro = {k: self.micro_baselines[k].z_score(v) for k, v in micro_scores.items()}
        z_macro = {k: self.macro_baselines[k].z_score(v) for k, v in macro_scores.items()}

        # EMA snapshot (for dashboard display)
        ema_snapshot = {
            f"micro.{k}": v.ema for k, v in self.micro_baselines.items()
        }
        ema_snapshot.update({
            f"macro.{k}": v.ema for k, v in self.macro_baselines.items()
        })

        # Detect dissonance
        events = self._detect_dissonance(z_micro, z_macro, document_id)

        return WindowAnalysisResult(
            z_scores_micro=z_micro,
            z_scores_macro=z_macro,
            ema_snapshot=ema_snapshot,
            dissonance_events=events,
        )

    # ------------------------------------------------------------------
    # Baseline snapshot export (for DB persistence)
    # ------------------------------------------------------------------

    def get_baseline_snapshot(self) -> Dict[str, Dict]:
        return {
            "micro": {k: v.to_dict() for k, v in self.micro_baselines.items()},
            "macro": {k: v.to_dict() for k, v in self.macro_baselines.items()},
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_micro(self, key: str, value: float) -> None:
        if key not in self.micro_baselines:
            self.micro_baselines[key] = BaselineStats()
        self.micro_baselines[key].update(value, self.alpha)

    def _update_macro(self, key: str, value: float) -> None:
        if key not in self.macro_baselines:
            self.macro_baselines[key] = BaselineStats()
        self.macro_baselines[key].update(value, self.alpha)

    def _detect_dissonance(
        self,
        z_micro: Dict[str, float],
        z_macro: Dict[str, float],
        document_id: str,
    ) -> List[DissonanceEvent]:
        events: List[DissonanceEvent] = []

        # Evaluate all defined semantic bridge pairs
        for micro_key, macro_key in _COMPARISON_BRIDGE:
            if micro_key not in z_micro or macro_key not in z_macro:
                continue
            z_m = z_micro[micro_key]
            z_M = z_macro[macro_key]
            delta = abs(z_M - z_m)

            if delta > self.threshold:
                events.append(DissonanceEvent(
                    event_id=f"dis_{uuid.uuid4().hex[:6]}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source_document_id=document_id,
                    trigger_type="Macro-Micro Conflict",
                    vectors_involved=[micro_key, macro_key],
                    delta_score=round(delta, 4),
                    algorithmic_conclusion=self._classify(delta, z_m, z_M),
                ))

        # Fallback: pair all micro vs macro by rank when bridge produces no results
        if not events and z_micro and z_macro:
            sorted_micro = sorted(z_micro.items(), key=lambda x: abs(x[1]), reverse=True)
            sorted_macro = sorted(z_macro.items(), key=lambda x: abs(x[1]), reverse=True)
            for (mk, mval), (Mk, Mval) in zip(sorted_micro[:3], sorted_macro[:3]):
                delta = abs(Mval - mval)
                if delta > self.threshold:
                    events.append(DissonanceEvent(
                        event_id=f"dis_{uuid.uuid4().hex[:6]}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source_document_id=document_id,
                        trigger_type="Macro-Micro Conflict (ranked fallback)",
                        vectors_involved=[mk, Mk],
                        delta_score=round(delta, 4),
                        algorithmic_conclusion=self._classify(delta, mval, Mval),
                    ))

        return events

    def _classify(self, delta: float, z_micro: float, z_macro: float) -> str:
        """Assign a human-readable label to a dissonance event."""
        if delta > 4.0:
            return (
                "Psychological Fracture — extreme divergence between conscious framing "
                "and subconscious signal. Possible dissociation or AI-generated text."
            )
        if z_macro > z_micro:
            return (
                "Posturing — conscious framing exceeds subconscious intensity. "
                "Possible ghostwriting, performance, or deliberate image construction."
            )
        return (
            "Suppressed Signal — subconscious intensity exceeds conscious framing. "
            "Possible emotional concealment or steganographic layering."
        )
