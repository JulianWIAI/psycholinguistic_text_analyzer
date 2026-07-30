"""
pds_layer/pds_analyzer.py
═══════════════════════════════════════════════════════════════════
Ousiometric PDS Payload Analyser — Full 8-Axis Affect Pipeline
═══════════════════════════════════════════════════════════════════

Computes the Power-Danger-Structure emotional profile of an intercept
text by delegating tokenization and lexicon I/O entirely to the
existing VAD layer, then applying the mathematical rotation defined in
pds_transformer.py.

8-Axis Affect Intensity layer (Session 5)
─────────────────────────────────────────
Every PDS-matched word is cross-referenced against all 8 NRC Affect
Intensity dimensions (Mohammad 2018):

  Primary threat axes (Session 4):
    anger, fear

  Extended palette (Session 5):
    anticipation, trust, surprise, sadness, joy, disgust

These scores power the three compound psychological trigger rules
evaluated on the frontend:

  1. Weaponized Escalation
       Apex Threat (+P,+D) AND (anger_μ > 0.750 OR anger_σ > 0.4)

  2. Weaponized Contempt  (Dehumanization precursor)
       Apex Threat (+P,+D) AND anger_μ > 0.6 AND disgust_μ > 0.5

  3. Paranoia / Hyper-Vigilance
       Desperate Panic (−P,+D) AND fear_μ > 0.6 AND anticipation_μ > 0.6

All affect scores degrade gracefully to 0.0 if lexicon files are absent.

Output schema
─────────────
{
  "power_mean":      float,   # μ Power ∈ [–1, +1]
  "power_sigma":     float,   # σ Power (inter-word volatility)
  "danger_mean":     float,
  "danger_sigma":    float,
  "structure_mean":  float,
  "structure_sigma": float,
  "anger_mean":      float,   # μ Anger intensity ∈ [0, 1]
  "anger_sigma":     float,
  "fear_mean":       float,
  "fear_sigma":      float,
  "ant_mean":        float,   # μ Anticipation intensity ∈ [0, 1]
  "ant_sigma":       float,
  "tru_mean":        float,   # μ Trust intensity ∈ [0, 1]
  "tru_sigma":       float,
  "sur_mean":        float,   # μ Surprise intensity ∈ [0, 1]
  "sur_sigma":       float,
  "sad_mean":        float,   # μ Sadness intensity ∈ [0, 1]
  "sad_sigma":       float,
  "joy_mean":        float,   # μ Joy intensity ∈ [0, 1]
  "joy_sigma":       float,
  "dis_mean":        float,   # μ Disgust intensity ∈ [0, 1]
  "dis_sigma":       float,
  "matched_count":   int,     # tokens with VAD scores in lexicon
  "total_tokens":    int,     # total non-stop content tokens examined
  "words":           list,    # top-N [{word, p, d, s, v, a, d_vad,
                               #         anger, fear, ant, tru, sur, sad, joy, dis}]
  "language":        str,
  "error":           str|None,
}

The "words" array is capped at _TOP_N_WORDS entries, ranked by
Euclidean distance from the PDS origin (√(P² + D²)), so the scatter
plot always shows the semantically most extreme words first.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from pds_layer.pds_transformer import vad_to_pds
from pds_layer.affect_loader import load_affect_pack   # Session 6: combined pack loader

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum number of word entries returned in the "words" scatter payload.
# All words are used for aggregate statistics; only the top-N are serialised
# into the response JSON to keep the payload manageable for large texts.
_TOP_N_WORDS: int = 60

# ---------------------------------------------------------------------------
# Internal axis registry
# ---------------------------------------------------------------------------
# Each entry: (short_key, affect_loader_label)
# The short_key becomes the word-dict field name and the aggregate prefix.
# Adding a new axis in future only requires one entry here + frontend columns.
_AFFECT_AXES: List[tuple] = [
    ("anger", "anger"),
    ("fear",  "fear"),
    ("ant",   "anticipation"),
    ("tru",   "trust"),
    ("sur",   "surprise"),
    ("sad",   "sadness"),
    ("joy",   "joy"),
    ("dis",   "disgust"),
]

# ---------------------------------------------------------------------------
# Statistical helpers
# (Local copies to avoid circular imports; identical to vad_layer versions.)
# ---------------------------------------------------------------------------

def _mean(xs: List[float]) -> float:
    """Arithmetic mean of a non-empty list — caller guarantees len ≥ 1."""
    return sum(xs) / len(xs)


def _population_std(xs: List[float], mu: Optional[float] = None) -> float:
    """
    Population standard deviation (σ).
    Returns 0.0 for single-element lists to avoid spurious precision.
    """
    if len(xs) < 2:
        return 0.0
    mu = mu if mu is not None else _mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs))


def _r4(x: float) -> float:
    """Round to 4 decimal places — keeps JSON payloads readable."""
    return round(x, 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_ousiometrics(text: str, lang: str) -> Dict[str, Any]:
    """
    Compute the Ousiometric Power-Danger-Structure profile of *text*,
    augmented with all 8 NRC Affect Intensity dimensions per word.

    The function delegates all tokenization and lexicon I/O to
    vad_layer.vad_analyzer.analyze_vad() then applies the PDS rotation
    to every matched word and cross-references each against the full
    8-axis affect-intensity palette.

    Parameters
    ----------
    text : str
        Raw intercept text (any length).  Very short texts will yield
        low lexicon coverage and wide confidence intervals.
    lang : str
        ISO-style language code: EN, DE, RU, ZH, AR, FA, KO, ES, FR, JA.

    Returns
    -------
    dict — see module docstring for full field list.  Always returns a
    valid dict; errors are reported in the ``error`` field (HTTP 200).

    Side effects
    ────────────
    None.  The function is idempotent and thread-safe; all statefulness
    lives in the lru_cache'd lexicons and spaCy model registry, both of
    which are read-only after initial load.
    """
    lang = lang.strip().upper()

    # Neutral/zero-point fallback — returned on any early exit.
    _EMPTY: Dict[str, Any] = {
        "power_mean":      0.0,
        "power_sigma":     0.0,
        "danger_mean":     0.0,
        "danger_sigma":    0.0,
        "structure_mean":  0.0,
        "structure_sigma": 0.0,
        # 8 affect axes × 2 stats each — all zero at the origin.
        "anger_mean":  0.0, "anger_sigma": 0.0,
        "fear_mean":   0.0, "fear_sigma":  0.0,
        "ant_mean":    0.0, "ant_sigma":   0.0,
        "tru_mean":    0.0, "tru_sigma":   0.0,
        "sur_mean":    0.0, "sur_sigma":   0.0,
        "sad_mean":    0.0, "sad_sigma":   0.0,
        "joy_mean":    0.0, "joy_sigma":   0.0,
        "dis_mean":    0.0, "dis_sigma":   0.0,
        "matched_count":   0,
        "total_tokens":    0,
        "words":           [],
        "language":        lang,
        "error":           None,
    }

    # ── 1. Obtain per-word VAD scores from the shared VAD layer ──────────
    # Deferred import to avoid circular load-order issues if the FastAPI
    # application imports pds_layer before vad_layer is fully initialised.
    try:
        from vad_layer.vad_analyzer import analyze_vad
    except ImportError as exc:
        return {**_EMPTY, "error": f"Could not import VAD layer: {exc}"}

    vad_result: Dict[str, Any] = analyze_vad(text, lang)

    # Propagate any VAD-layer diagnostics (missing lexicon, model, etc.)
    if vad_result.get("error"):
        return {
            **_EMPTY,
            "total_tokens": vad_result.get("total_tokens", 0),
            "error": vad_result["error"],
        }

    vad_words: List[Dict[str, Any]] = vad_result.get("words", [])
    if not vad_words:
        return {
            **_EMPTY,
            "total_tokens": vad_result.get("total_tokens", 0),
            "error": (
                "No lexicon matches were available for the PDS transformation.  "
                "Ensure the NRC-VAD lexicon TSV for this language is installed and "
                "the intercept text is sufficiently long for adequate coverage."
            ),
        }

    # ── 2. Load the full 8-axis affect pack for this language ────────────────
    # Session 6: a single call reads the combined intensity_{lang}.txt file
    # (all 8 emotions in one 4-column TSV) and caches the result keyed only
    # on lang — replacing 8 individual per-affect loads with one cache hit.
    #
    # Fallback chain (handled inside affect_loader / affect_path_resolver):
    #   Tier 1 — language-specific combined file  (e.g. intensity_ru.txt)
    #   Tier 2 — English combined base file       (intensity_en.txt)
    #   Tier 3 — empty AffectPack                 (file not installed → 0.0)
    affect_pack = load_affect_pack(lang)   # AffectPack: {emotion: {word: score}}

    # Slice out each short-key axis from the pack into the flat lookup dict
    # used by the per-word cross-reference loop below.
    affect_lexicons: Dict[str, Dict[str, float]] = {
        short_key: affect_pack.get(label, {})
        for short_key, label in _AFFECT_AXES
    }

    # ── 3. Apply VAD → PDS rotation + 8-axis affect cross-reference ───────
    p_vals: List[float] = []
    d_vals: List[float] = []
    s_vals: List[float] = []
    # Accumulator lists for each affect axis (keyed by short axis name).
    affect_vals: Dict[str, List[float]] = {key: [] for key, _ in _AFFECT_AXES}

    pds_words: List[Dict[str, Any]] = []

    for w in vad_words:
        v_raw: float = w["v"]
        a_raw: float = w["a"]
        d_raw: float = w["d"]   # NRC Dominance (not PDS Danger)

        power, danger, structure = vad_to_pds(v_raw, a_raw, d_raw)

        p_vals.append(power)
        d_vals.append(danger)
        s_vals.append(structure)

        # Cross-reference against every affect lexicon.
        # The VAD layer already lower-cases tokens; affect lexicons use the
        # same lowercase surface-form convention, so no extra normalisation needed.
        word_lower: str = w["word"].lower()
        word_affect: Dict[str, float] = {
            key: affect_lexicons[key].get(word_lower, 0.0)
            for key, _ in _AFFECT_AXES
        }
        for key, score in word_affect.items():
            affect_vals[key].append(score)

        pds_words.append({
            "word":  w["word"],
            "p":     _r4(power),
            "d":     _r4(danger),
            "s":     _r4(structure),
            # Pass raw VAD through so the frontend tooltip can show both
            # coordinate systems side-by-side.
            "v":     w["v"],
            "a":     w["a"],
            "d_vad": w["d"],
            # 8-axis affect intensities.
            # 0.0 means "not in affect lexicon" — distinct from zero intensity.
            **{key: _r4(score) for key, score in word_affect.items()},
        })

    # ── 4. Compute aggregate statistics for all axes ──────────────────────
    p_mu: float = _mean(p_vals)
    d_mu: float = _mean(d_vals)
    s_mu: float = _mean(s_vals)
    affect_mu:    Dict[str, float] = {k: _mean(v)             for k, v in affect_vals.items()}
    affect_sigma: Dict[str, float] = {k: _population_std(v, affect_mu[k])
                                       for k, v in affect_vals.items()}

    # ── 5. Rank by P-D extremity; cap payload at _TOP_N_WORDS ─────────────
    # Sort descending by Euclidean distance from the PDS origin in the
    # Power × Danger plane.  Words near the origin are semantically neutral
    # and clutter the scatter plot without adding analytical value.
    pds_words.sort(
        key=lambda w: (w["p"] ** 2 + w["d"] ** 2) ** 0.5,
        reverse=True,
    )
    top_words = pds_words[:_TOP_N_WORDS]

    # ── 6. Assemble and return the full response dict ─────────────────────
    return {
        "power_mean":      _r4(p_mu),
        "power_sigma":     _r4(_population_std(p_vals, p_mu)),
        "danger_mean":     _r4(d_mu),
        "danger_sigma":    _r4(_population_std(d_vals, d_mu)),
        "structure_mean":  _r4(s_mu),
        "structure_sigma": _r4(_population_std(s_vals, s_mu)),
        # Flatten 8-axis affect stats into top-level keys:
        #   anger_mean, anger_sigma, fear_mean, fear_sigma, ant_mean, … dis_sigma
        **{f"{k}_mean":  _r4(affect_mu[k])    for k, _ in _AFFECT_AXES},
        **{f"{k}_sigma": _r4(affect_sigma[k]) for k, _ in _AFFECT_AXES},
        "matched_count":   len(p_vals),
        "total_tokens":    vad_result.get("total_tokens", len(p_vals)),
        "words":           top_words,
        "language":        lang,
        "error":           None,
    }
