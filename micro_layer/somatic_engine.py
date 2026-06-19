"""
micro_layer/somatic_engine.py — Somatic/Archetypal Cipher Engine (Python reference).

This module is the authoritative pure-Python implementation and the permanent
fallback when the compiled _somatic_core C++ extension is not available.

Numeric & Categorical Matrix (exact specification)
──────────────────────────────────────────────────────────────────────────────
  A =  1  Origin    | B =  2  Kinetic   | C =  3  Resonant  | D =  4  Sovereign
  E =  5  Kinetic   | F =  6  Kinetic   | G =  7  Liminal   | H =  8  Resonant
  I =  9  Sovereign | J = 10  Kinetic   | K = 11  Sovereign | L = 12  Resonant
  M = 13  Resonant  | N = 14  Liminal   | O = 15  Resonant  | P = 16  Kinetic
  Q = 17  Sovereign | R = 18  Liminal   | S = 19  Kinetic   | T = 20  Sovereign
  U = 21  Resonant  | V = 22  Kinetic   | W = 23  Sovereign | X = 24  Sovereign
  Y = 25  Resonant  | Z = 26  Sovereign
  Ä = 1.5  Liminal  | Ö = 15.5  Liminal | Ü = 21.5  Liminal

Complexity Tiers (per-word population σ):
  T1 — σ < 2.0  : Somatic / Universal
  T2 — 2 ≤ σ < 5: Archetypal Bridge
  T3 — σ ≥ 5   : State / System

Quersumme Archetypes:
  1 Source | 2 Bond | 3 Overflow | 4 Foundation | 5 Friction
  6 Grounding | 7 Precursor | 8 Infinity/State | 9 Transcendent

Spectral Analysis:
  micro_wavelength  — ordered array of first 256 letter values in the window
                      (zero-padded to exactly 256)
  top_harmonics     — top 5 non-DC FFT bins by magnitude (via numpy)
  global_waveform_envelope — 100-bucket average computed from the FULL document
                             (call compute_global_envelope(); NOT part of
                              per-window SomaticResult)
"""

import math
import re
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Optional numpy (for FFT) ──────────────────────────────────────────────────
try:
    import numpy as _np
    _NUMPY = True
except ImportError:
    _np = None
    _NUMPY = False
    warnings.warn(
        "numpy not found — FFT harmonics disabled. Install with: pip install numpy",
        RuntimeWarning, stacklevel=1,
    )

# ── Optional C++ core ─────────────────────────────────────────────────────────
try:
    import _somatic_core as _cpp
    _CPP = True
except ImportError:
    _cpp = None
    _CPP = False

# ── Optional JA bridge ────────────────────────────────────────────────────────
from micro_layer.ja_romaji_bridge import to_romaji as _ja_to_romaji
from micro_layer.ja_romaji_bridge import is_available as _ja_available


# ════════════════════════════════════════════════════════════════════════════
# Numeric & category tables
# ════════════════════════════════════════════════════════════════════════════

# (value, category) for every A–Z and umlaut
_LETTER_TABLE: Dict[str, Tuple[float, str]] = {
    "A": ( 1.0, "origin"),    "B": ( 2.0, "kinetic"),
    "C": ( 3.0, "resonant"),  "D": ( 4.0, "sovereign"),
    "E": ( 5.0, "kinetic"),   "F": ( 6.0, "kinetic"),
    "G": ( 7.0, "liminal"),   "H": ( 8.0, "resonant"),
    "I": ( 9.0, "sovereign"), "J": (10.0, "kinetic"),
    "K": (11.0, "sovereign"), "L": (12.0, "resonant"),
    "M": (13.0, "resonant"),  "N": (14.0, "liminal"),
    "O": (15.0, "resonant"),  "P": (16.0, "kinetic"),
    "Q": (17.0, "sovereign"), "R": (18.0, "liminal"),
    "S": (19.0, "kinetic"),   "T": (20.0, "sovereign"),
    "U": (21.0, "resonant"),  "V": (22.0, "kinetic"),
    "W": (23.0, "sovereign"), "X": (24.0, "sovereign"),
    "Y": (25.0, "resonant"),  "Z": (26.0, "sovereign"),
    # German umlauts — Liminal half-steps
    "Ä": ( 1.5, "liminal"),
    "Ö": (15.5, "liminal"),
    "Ü": (21.5, "liminal"),
}

# Normalise common diacritics so Latin-alphabet languages also benefit
# (e.g. Spanish É/Á → E/A before table lookup)
_DIACRITIC_MAP = str.maketrans(
    "ÁÀÂÃÅáàâãåÉÈÊéèêÍÌÎíìîÓÒÔÕóòôõÚÙÛúùûÑñÇçÝý",
    "AAAAAaaaaáEEEeeéIIIiiiOOOOooooUUUuuuNnCcYy"
)


# ════════════════════════════════════════════════════════════════════════════
# Quersumme archetypes
# ════════════════════════════════════════════════════════════════════════════

QUERSUMME_ARCHETYPES: Dict[int, str] = {
    1: "1 — Source: the undivided origin point, pure potential",
    2: "2 — Bond: duality and connection, the first relation",
    3: "3 — Overflow: creative expression spilling beyond containers",
    4: "4 — Foundation: law, structure, systemic stability",
    5: "5 — Friction: instability and kinetic transit between states",
    6: "6 — Grounding: harmonic equilibrium, aesthetic resolution",
    7: "7 — Precursor: the liminal threshold before emergence",
    8: "8 — Infinity/State: sovereign will, institutional recursion",
    9: "9 — Transcendent: full-cycle integration and dissolution",
}

COMPLEXITY_TIERS: Dict[int, Tuple[str, str]] = {
    1: ("T1", "Somatic / Universal"),
    2: ("T2", "Archetypal Bridge"),
    3: ("T3", "State / System"),
}

_N_FFT = 256  # Must be a power of 2; matches the C++ engine


# ════════════════════════════════════════════════════════════════════════════
# Result dataclasses
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class SomaticResult:
    """
    Per-window output from SomaticEngine.analyze().

    Fields correspond exactly to the C++ WindowResult + archetype strings so
    that api/routes.py can consume either without branching.
    """
    avg_word_sigma:      float = 0.0
    dominant_quersumme:  int   = 0
    quersumme_archetype: str   = ""
    tier_code:           str   = "T1"
    tier_label:          str   = "Somatic / Universal"

    # Category fractions (all letters in window)
    somatic_score:      float = 0.0   # Origin  (A)
    sovereignty_score:  float = 0.0   # Sovereign (D I K Q T W X Z)
    resonant_score:     float = 0.0   # Resonant  (C H L M O U Y)
    kinetic_score:      float = 0.0   # Kinetic   (B E F J P S V)
    liminal_score:      float = 0.0   # Liminal   (Ä G N R Ö Ü)

    tier_distribution:  Dict[int, int]  = field(default_factory=dict)
    category_counts:    Dict[str, int]  = field(default_factory=dict)
    word_scatter:       List[Dict]      = field(default_factory=list)

    # Spectral payloads
    micro_wavelength:   List[float]     = field(default_factory=list)
    top_harmonics:      List[Dict]      = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "avg_word_sigma":      round(self.avg_word_sigma, 4),
            "dominant_quersumme":  self.dominant_quersumme,
            "quersumme_archetype": self.quersumme_archetype,
            "tier_code":           self.tier_code,
            "tier_label":          self.tier_label,
            "somatic_score":       round(self.somatic_score, 4),
            "sovereignty_score":   round(self.sovereignty_score, 4),
            "resonant_score":      round(self.resonant_score, 4),
            "kinetic_score":       round(self.kinetic_score, 4),
            "liminal_score":       round(self.liminal_score, 4),
            "tier_distribution":   self.tier_distribution,
            "category_counts":     self.category_counts,
            "word_scatter":        self.word_scatter,
            "micro_wavelength":    [round(v, 3) for v in self.micro_wavelength],
            "top_harmonics":       self.top_harmonics,
        }


# ════════════════════════════════════════════════════════════════════════════
# Internal pure-Python helpers
# ════════════════════════════════════════════════════════════════════════════

_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüÁÀÂáàâÉÈÊéèêÍÌÎíìîÓÒÔóòôÚÙÛúùûÑñÇçÝý]+")


def _normalise(text: str) -> str:
    """Apply diacritic normalisation so é→E, etc. feed the table correctly."""
    return text.translate(_DIACRITIC_MAP)


def _iter_letter_pairs(text: str):
    """Yield (value, category) for every character found in _LETTER_TABLE."""
    for ch in text.upper():
        entry = _LETTER_TABLE.get(ch)
        if entry is not None:
            yield entry  # (value, category)


def _pop_sigma(values: List[float]) -> float:
    """Population standard deviation (σ, not sample s)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def _digital_root(n: int) -> int:
    """Quersumme — reduce to single digit 1–9."""
    if n <= 0:
        return 0
    r = n % 9
    return r if r != 0 else 9


def _dominant_tier(tier_dist: Dict[int, int]) -> int:
    if not tier_dist:
        return 1
    return max(tier_dist, key=lambda k: tier_dist[k])


def _fft_harmonics(signal: List[float], n_fft: int = _N_FFT, top_k: int = 5) -> List[Dict]:
    """Return top-k spectral peaks via numpy FFT, or [] if numpy unavailable.

    DC offset is removed (mean subtracted) before the FFT so that a large
    average letter value cannot dominate bins 1-5 via spectral leakage,
    masking genuine rhythmic steganographic structures.
    """
    if not _NUMPY:
        return []
    real = signal[:n_fft]                         # take at most n_fft samples
    arr  = _np.zeros(n_fft, dtype=_np.float32)
    n    = len(real)
    if n == 0:
        return []
    arr[:n] = real

    # ── DC offset removal: subtract mean of real (non-padded) samples ────────
    mean   = float(_np.mean(arr[:n]))
    arr[:n] -= mean
    # zero-padded tail stays at 0 — already mean-free relative to itself

    spectrum = _np.fft.rfft(arr)
    mags = _np.abs(spectrum)      # shape: (n_fft//2 + 1,)
    # Skip DC bin 0 (now effectively zero after mean subtraction)
    search  = mags[1: n_fft // 2]
    top_idx = _np.argsort(search)[-top_k:][::-1]
    peaks = []
    for idx in top_idx:
        bin_num = int(idx) + 1
        peaks.append({
            "bin":       bin_num,
            "magnitude": round(float(mags[bin_num]), 4),
            "norm_freq": round(float(bin_num) / n_fft, 6),
        })
    return peaks


# ════════════════════════════════════════════════════════════════════════════
# SomaticEngine
# ════════════════════════════════════════════════════════════════════════════

class SomaticEngine:
    """
    Somatic/Archetypal Cipher Engine.

    Automatically delegates to the compiled _somatic_core C++ extension when
    available; falls back to the pure-Python implementation otherwise.

    Public methods
    --------------
    analyze(text, language='EN') -> SomaticResult
        Per-window analysis.  For JA text, converts Kana/Kanji to Romaji
        first (requires pykakasi).

    compute_global_envelope(full_text, language='EN') -> List[float]
        100-bucket energy envelope computed from the ENTIRE document.
        Returns a list of 100 floats — one per bucket.  Attach this to the
        document-level result, not per-window.
    """

    # ------------------------------------------------------------------
    # Public: per-window analysis
    # ------------------------------------------------------------------

    def analyze(self, text: str, language: str = "EN") -> SomaticResult:
        processed = self._preprocess(text, language)

        if _CPP:
            return self._from_cpp(_cpp.analyze(processed))
        return self._py_analyze(processed)

    # ------------------------------------------------------------------
    # Public: full-document global envelope
    # ------------------------------------------------------------------

    def compute_global_envelope(
        self, full_text: str, language: str = "EN", n_buckets: int = 100
    ) -> List[float]:
        processed = self._preprocess(full_text, language)

        if _CPP:
            return list(_cpp.compute_global_envelope(processed, n_buckets))
        return self._py_global_envelope(processed, n_buckets)

    # ------------------------------------------------------------------
    # Preprocessing — language-specific text preparation
    # ------------------------------------------------------------------

    def _preprocess(self, text: str, language: str) -> str:
        if language == "JA":
            if _ja_available():
                return _ja_to_romaji(text)
            warnings.warn(
                "JA Romaji bridge unavailable — somatic analysis will score "
                "zero letters for Japanese text. Install pykakasi.",
                RuntimeWarning, stacklevel=3,
            )
        return _normalise(text)

    # ------------------------------------------------------------------
    # C++ result adapter
    # ------------------------------------------------------------------

    @staticmethod
    def _from_cpp(d: Dict) -> SomaticResult:
        """Wrap a dict returned by _somatic_core.analyze() into SomaticResult."""
        qs = d.get("dominant_quersumme", 0)
        return SomaticResult(
            avg_word_sigma      = d.get("avg_word_sigma", 0.0),
            dominant_quersumme  = qs,
            quersumme_archetype = d.get("quersumme_archetype",
                                        QUERSUMME_ARCHETYPES.get(qs, "")),
            tier_code           = d.get("tier_code", "T1"),
            tier_label          = d.get("tier_label", "Somatic / Universal"),
            somatic_score       = d.get("somatic_score", 0.0),
            sovereignty_score   = d.get("sovereignty_score", 0.0),
            resonant_score      = d.get("resonant_score", 0.0),
            kinetic_score       = d.get("kinetic_score", 0.0),
            liminal_score       = d.get("liminal_score", 0.0),
            tier_distribution   = {int(k): v for k, v in d.get("tier_distribution", {}).items()},
            category_counts     = dict(d.get("category_counts", {})),
            word_scatter        = list(d.get("word_scatter", [])),
            micro_wavelength    = list(d.get("micro_wavelength", [])),
            top_harmonics       = list(d.get("top_harmonics", [])),
        )

    # ------------------------------------------------------------------
    # Pure-Python analysis
    # ------------------------------------------------------------------

    def _py_analyze(self, text: str) -> SomaticResult:
        words = _WORD_RE.findall(text)
        if not words:
            return SomaticResult()

        cat_counts: Dict[str, int] = {
            "origin": 0, "kinetic": 0, "resonant": 0,
            "sovereign": 0, "liminal": 0,
        }
        tier_dist: Dict[int, int] = {1: 0, 2: 0, 3: 0}
        sigma_sum  = 0.0
        qsum_freq: Dict[int, int] = {}
        word_scatter: List[Dict] = []
        raw_signal: List[float] = []

        for raw in words:
            pairs = list(_iter_letter_pairs(raw))
            if not pairs:
                continue

            vals = [v for v, _ in pairs]
            word_sum = sum(vals)
            sigma    = _pop_sigma(vals)
            dr       = _digital_root(int(round(word_sum)))
            tier     = 1 if sigma < 2.0 else (2 if sigma < 5.0 else 3)

            # Dominant category (plurality)
            cat_freq: Dict[str, int] = {}
            for _, cat in pairs:
                cat_freq[cat] = cat_freq.get(cat, 0) + 1
            dom_cat = max(cat_freq, key=lambda k: cat_freq[k])

            word_scatter.append({
                "word": raw.upper(),
                "x":    round(word_sum, 2),
                "y":    round(sigma, 4),
                "dr":   dr,
                "cat":  dom_cat,
                "tier": tier,
            })

            sigma_sum += sigma
            tier_dist[tier] = tier_dist.get(tier, 0) + 1
            qsum_freq[dr]   = qsum_freq.get(dr, 0) + 1

            for _, cat in pairs:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            for v, _ in pairs:
                if len(raw_signal) < _N_FFT:
                    raw_signal.append(v)

        n_words = len(word_scatter)
        if n_words == 0:
            return SomaticResult()

        # Pad micro_wavelength to N_FFT
        micro_wl = raw_signal + [0.0] * (_N_FFT - len(raw_signal))

        # FFT harmonics
        top_harmonics = _fft_harmonics(raw_signal)

        # Aggregates
        avg_sigma    = sigma_sum / n_words
        dom_qs       = max(qsum_freq, key=lambda k: qsum_freq[k])
        dom_tier_id  = _dominant_tier(tier_dist)
        tier_code, tier_label = COMPLEXITY_TIERS[dom_tier_id]

        total_letters = max(1, sum(cat_counts.values()))
        tl = float(total_letters)

        return SomaticResult(
            avg_word_sigma      = avg_sigma,
            dominant_quersumme  = dom_qs,
            quersumme_archetype = QUERSUMME_ARCHETYPES.get(dom_qs, ""),
            tier_code           = tier_code,
            tier_label          = tier_label,
            somatic_score       = cat_counts["origin"]    / tl,
            sovereignty_score   = cat_counts["sovereign"] / tl,
            resonant_score      = cat_counts["resonant"]  / tl,
            kinetic_score       = cat_counts["kinetic"]   / tl,
            liminal_score       = cat_counts["liminal"]   / tl,
            tier_distribution   = tier_dist,
            category_counts     = cat_counts,
            word_scatter        = word_scatter,
            micro_wavelength    = micro_wl,
            top_harmonics       = top_harmonics,
        )

    # ------------------------------------------------------------------
    # Pure-Python global envelope
    # ------------------------------------------------------------------

    @staticmethod
    def _py_global_envelope(text: str, n_buckets: int = 100) -> List[float]:
        """Collect all letter values, then average into n_buckets bins."""
        all_values: List[float] = []
        for v, _ in _iter_letter_pairs(text):
            all_values.append(v)

        if not all_values:
            return [0.0] * n_buckets

        total  = len(all_values)
        result = []
        for b in range(n_buckets):
            start = (b * total) // n_buckets
            end   = ((b + 1) * total) // n_buckets
            if start >= end:
                result.append(0.0)
            else:
                bucket_vals = all_values[start:end]
                result.append(round(sum(bucket_vals) / len(bucket_vals), 4))
        return result
