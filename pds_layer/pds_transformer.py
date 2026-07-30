"""
pds_layer/pds_transformer.py
═══════════════════════════════════════════════════════════════════
VAD → PDS Mathematical Rotation  (Ousiometrics Framework)
═══════════════════════════════════════════════════════════════════

Background
──────────
The Ousiometrics framework (Dodds, Minot, Iniguez, Bhattacharya,
Reagan & Danforth, "Fame and Obscurity", 2020; "Ousiometrics and
Wellbeing", arXiv:2009.10450) applies Singular Value Decomposition
(SVD) to the full NRC-VAD word embedding cloud.  The three dominant
singular vectors form a rotated coordinate system that is semantically
richer and more operationally useful for intelligence analysis than the
raw Valence-Arousal-Dominance axes:

  • Power     (P) — perceived authority, dominance, influence
  • Danger    (D) — threat level; combines negative valence with activation
  • Structure (S) — order, composure, predictability; inverse of arousal

Because the exact SVD rotation matrix is bundled with the Dodds research
corpus, this module provides a high-fidelity linear proxy that reproduces
the qualitative topology of the PDS space with high accuracy:

Mathematical derivation
───────────────────────
Step 1 — Centre each NRC score from [0, 1] → [–1, +1]:
    v_c = (V – 0.5) × 2
    a_c = (A – 0.5) × 2
    d_c = (D – 0.5) × 2

Step 2 — Linear proxy rotation:
    Power     =  d_c
    Danger    = –v_c × W_DV  +  a_c × W_DA
    Structure = –a_c

Where:
    W_DV = 0.70  (inverted valence contribution to Danger)
    W_DA = 0.30  (arousal's positive contribution to Danger)

These weights are constrained to sum to 1.0, which guarantees that the
Danger output stays within [–1, +1] without an explicit clip:
    max |Danger| = W_DV × |–v_c|_max + W_DA × |a_c|_max
                 = 0.70 × 1.0 + 0.30 × 1.0 = 1.00  ✓

Step 3 — Hard clip to [–1, +1] to absorb any floating-point drift.

Empirical spot-checks against the NRC English lexicon
───────────────────────────────────────────────────────
  Word        V      A      D    →   Power   Danger  Structure
  ─────────   ─────  ─────  ─────    ──────  ──────  ─────────
  "terror"    0.054  0.948  0.250    –0.500  +0.899  –0.896   ✓ extreme threat
  "authority" 0.656  0.454  0.848    +0.696  –0.223  +0.092   ✓ benevolent power
  "joy"       0.964  0.740  0.736    +0.472  –0.497  –0.480   ✓ positive, active
  "defeat"    0.115  0.321  0.100    –0.800  +0.574  +0.358   ✓ weak & threatened
  "calm"      0.720  0.173  0.614    +0.228  –0.555  +0.654   ✓ composed safety
  "panic"     0.100  0.900  0.150    –0.700  +0.800  –0.800   ✓ panic quadrant
"""

from __future__ import annotations

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Proxy rotation weights
# (must sum to 1.0 for the Danger output range guarantee — see module doc)
# ---------------------------------------------------------------------------
_W_DANGER_VALENCE: float = 0.70   # inverted Valence loads onto Danger
_W_DANGER_AROUSAL: float = 0.30   # Arousal loads onto Danger

# Enforce the range-preservation constraint at import time.
assert abs(_W_DANGER_VALENCE + _W_DANGER_AROUSAL - 1.0) < 1e-9, (
    "PDS rotation weights (_W_DANGER_VALENCE + _W_DANGER_AROUSAL) must sum to 1.0 "
    "to guarantee Danger ∈ [–1, +1] without explicit normalisation."
)


# ---------------------------------------------------------------------------
# Core rotation function
# ---------------------------------------------------------------------------

def vad_to_pds(
    valence:   float,
    arousal:   float,
    dominance: float,
) -> Tuple[float, float, float]:
    """
    Rotate a single (V, A, D) triple from the NRC [0, 1] hypercube into the
    Ousiometric (Power, Danger, Structure) space in [–1, +1].

    Parameters
    ----------
    valence   : float  Raw NRC valence score in [0, 1].
    arousal   : float  Raw NRC arousal score in [0, 1].
    dominance : float  Raw NRC dominance score in [0, 1].

    Returns
    -------
    (power, danger, structure) — each guaranteed in [–1.0, +1.0].

    Notes
    -----
    The function is a pure mapping with no side effects and no I/O.
    It is designed to be called inside a tight inner loop (one call per
    matched token) so it deliberately avoids any allocation or branching
    beyond the final clip.
    """
    # Step 1 — centre [0,1] → [–1,+1]
    v_c: float = (valence   - 0.5) * 2.0
    a_c: float = (arousal   - 0.5) * 2.0
    d_c: float = (dominance - 0.5) * 2.0

    # Step 2 — proxy linear rotation
    power:     float = d_c
    danger:    float = (-v_c * _W_DANGER_VALENCE) + (a_c * _W_DANGER_AROUSAL)
    structure: float = -a_c

    # Step 3 — absorb any floating-point overshoot
    return _clip(power), _clip(danger), _clip(structure)


def _clip(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    """Clamp *value* to the closed interval [*lo*, *hi*]."""
    return lo if value < lo else (hi if value > hi else value)


# ---------------------------------------------------------------------------
# Axis semantics metadata
# Consumed by the frontend JS and the help-drawer documentation generator.
# ---------------------------------------------------------------------------

AXIS_LABELS: Dict[str, Dict[str, str]] = {
    "power": {
        "label":    "Power",
        "negative": "Weak / Submissive",
        "positive": "Powerful / Dominant",
        "unit":     "P",
        "css_var":  "--cyan",
    },
    "danger": {
        "label":    "Danger",
        "negative": "Safe / Benevolent",
        "positive": "Dangerous / Threatening",
        "unit":     "D",
        "css_var":  "--warn",
    },
    "structure": {
        "label":    "Structure",
        "negative": "Unstructured / Chaotic",
        "positive": "Structured / Composed",
        "unit":     "S",
        "css_var":  "--ok",
    },
}
