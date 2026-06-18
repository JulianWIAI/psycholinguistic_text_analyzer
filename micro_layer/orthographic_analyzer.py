"""
MODULE 2 — Micro-Layer: Orthography & Phonosemantics  (English / Latin baseline)
Analyzes text at the character level using the visual geometry and
sound of letters.

Pipeline per word:
    1. Base Psychological Vectors (BPV) — per-letter integer weights
    2. Positional Modifiers (μ_p)       — start / middle / end multipliers
    3. Visual Complexity Anchors        — W, M, K trigger a word-level ×1.2
    4. Phonosemantic Multiplier (G_m)   — double-letter geometric override
    5. Interaction Coefficients (I_c)   — adjacent/near letter-pair overrides

Language subclasses (ES, FR) override the hook methods _double_gm() and
_pos_mult() to inject their phonological rules without duplicating logic.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from micro_layer.base_analyzer import BaseMicroAnalyzer, MicroResult

# ---------------------------------------------------------------------------
# 1. Base Psychological Vectors (BPV)
# ---------------------------------------------------------------------------
BPV: Dict[str, int] = {
    "A": 8,  "B": 7,  "C": 5,  "D": 6,  "E": 4,  "F": 6,
    "G": 5,  "H": 7,  "I": 9,  "J": 4,  "K": 8,  "L": 6,
    "M": 8,  "N": 7,  "O": 5,  "P": 7,  "Q": 6,  "R": 7,
    "S": 6,  "T": 7,  "U": 5,  "V": 6,  "W": 8,  "X": 7,
    "Y": 5,  "Z": 9,
}

# ---------------------------------------------------------------------------
# 2. Default positional multipliers
# ---------------------------------------------------------------------------
_POS_START  = 1.50   # first letter of a word
_POS_MIDDLE = 1.00   # any interior letter
_POS_END    = 0.75   # last letter of a word

# ---------------------------------------------------------------------------
# 3. Visual Complexity Anchors — word score ×1.2 if it contains any of these
# ---------------------------------------------------------------------------
_VISUAL_COMPLEXITY = frozenset({"W", "M", "K"})

# ---------------------------------------------------------------------------
# 4. Default phonosemantic classes for exact double letters
# ---------------------------------------------------------------------------
_SIBILANTS_FRICATIVES = frozenset("SFVZ")
_PLOSIVES             = frozenset("BDPTKG" "C")
_LIQUIDS_NASALS       = frozenset("LMNR")
_VOWELS               = frozenset("AEIOU")

_DEFAULT_DOUBLE_GM: Dict[str, float] = {}
for _c in _SIBILANTS_FRICATIVES: _DEFAULT_DOUBLE_GM[_c] = 1.8
for _c in _PLOSIVES:             _DEFAULT_DOUBLE_GM[_c] = 1.6
for _c in _LIQUIDS_NASALS:       _DEFAULT_DOUBLE_GM[_c] = 1.4
for _c in _VOWELS:               _DEFAULT_DOUBLE_GM[_c] = 1.3

# ---------------------------------------------------------------------------
# 5. Interaction Coefficients — canonical (sorted) pair key → (I_c, label, type)
# ---------------------------------------------------------------------------
_RAW_PAIRS = [
    ("H", "B", 1.5, "Security",               "syntonic"),
    ("K", "Z", 1.8, "Aggression",             "syntonic"),
    ("C", "O", 1.4, "Openness",               "syntonic"),
    ("S", "E", 0.8, "Suppressed Nervousness", "dystonic"),
    ("I", "C", 0.7, "Guarded Interaction",    "dystonic"),
    ("A", "S", 1.7, "Alertness",              "transformative"),
    ("M", "W", 2.0, "Emotional Turmoil",      "transformative"),
]
INTERACTION_PAIRS: Dict[Tuple[str, str], Tuple[float, str, str]] = {
    (min(a, b), max(a, b)): (ic, label, itype)
    for a, b, ic, label, itype in _RAW_PAIRS
}


# ---------------------------------------------------------------------------
# Internal result dataclasses (used within the Latin-script pipeline)
# ---------------------------------------------------------------------------

@dataclass
class DoubleLetter:
    word: str
    pair: str
    gm: float
    score: float


@dataclass
class InteractionEvent:
    word: str
    pair: str
    label: str
    interaction_type: str
    i_c: float
    p_d: float
    score: float


@dataclass
class MicroScore:
    """Internal rich result — not the public interface; see MicroResult."""
    raw_score: float = 0.0
    total_chars: int = 1
    letter_totals: Dict[str, float] = field(default_factory=dict)
    interaction_events: List[InteractionEvent] = field(default_factory=list)
    double_letter_events: List[DoubleLetter] = field(default_factory=list)
    words_with_visual_complexity: int = 0


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class OrthographicAnalyzer(BaseMicroAnalyzer):
    """
    English (and generic Latin-script) orthographic analyzer.

    Subclasses override two hooks:
        _double_gm(letter)            → float  (phonosemantic multiplier)
        _pos_mult(pos, last_idx, ch)  → float  (positional multiplier)

    The public analyze() method converts the internal MicroScore into a
    standardized MicroResult so the dissonance engine receives uniform input.
    """

    _WORD_RE = re.compile(r"[A-Za-z]+")

    @property
    def language_code(self) -> str:
        return "EN"

    # ------------------------------------------------------------------
    # Public interface — returns standardized MicroResult
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> MicroResult:
        score = self._score(text)
        return self._to_result(score)

    # ------------------------------------------------------------------
    # Hook methods — override in subclasses for phonological overrides
    # ------------------------------------------------------------------

    def _double_gm(self, letter: str) -> float:
        """Geometric multiplier for an exact double letter (e.g. 'ss', 'll')."""
        return _DEFAULT_DOUBLE_GM.get(letter, 1.0)

    def _pos_mult(self, pos: int, last_idx: int, char: str) -> float:
        """Positional multiplier for a single character in a word."""
        if pos == 0:
            return _POS_START
        if pos == last_idx:
            return _POS_END
        return _POS_MIDDLE

    # ------------------------------------------------------------------
    # Internal scoring engine
    # ------------------------------------------------------------------

    def _score(self, text: str) -> MicroScore:
        """Full Latin-script scoring pipeline — returns internal MicroScore."""
        words = self._WORD_RE.findall(text)
        total = 0.0
        total_chars = 0
        letter_totals: Dict[str, float] = {}
        all_interactions: List[InteractionEvent] = []
        all_doubles: List[DoubleLetter] = []
        visual_count = 0

        for raw_word in words:
            word = raw_word.upper()
            total_chars += len(word)
            word_score, interactions, doubles, has_visual = self._score_word(word)
            total += word_score
            if has_visual:
                visual_count += 1
            all_interactions.extend(interactions)
            all_doubles.extend(doubles)
            for ch in word:
                if ch in BPV:
                    letter_totals[ch] = letter_totals.get(ch, 0.0) + BPV[ch]

        return MicroScore(
            raw_score=total,
            total_chars=max(1, total_chars),
            letter_totals=letter_totals,
            interaction_events=all_interactions,
            double_letter_events=all_doubles,
            words_with_visual_complexity=visual_count,
        )

    def _score_word(
        self, word: str
    ) -> Tuple[float, List[InteractionEvent], List[DoubleLetter], bool]:
        """
        Score a single uppercase word through all five micro-layer rules.
        Uses the hook methods _double_gm() and _pos_mult() so subclasses
        can inject language-specific phonological rules.
        """
        interactions: List[InteractionEvent] = []
        doubles: List[DoubleLetter] = []
        consumed: Dict[int, float] = {}  # pos → override contribution

        # ── Rule 4: Double Letters ────────────────────────────────────
        i = 0
        while i < len(word) - 1:
            if word[i] == word[i + 1]:
                letter = word[i]
                gm = self._double_gm(letter)
                pair_score = BPV.get(letter, 0) * gm
                doubles.append(DoubleLetter(word=word, pair=letter * 2, gm=gm, score=pair_score))
                consumed[i]     = pair_score / 2
                consumed[i + 1] = pair_score / 2
                i += 2
            else:
                i += 1

        # ── Rule 5: Interaction Coefficient Pairs ─────────────────────
        n = len(word)
        for idx_a in range(n):
            for idx_b in range(idx_a + 1, min(idx_a + 3, n)):
                distance = idx_b - idx_a
                key = (min(word[idx_a], word[idx_b]), max(word[idx_a], word[idx_b]))
                if key not in INTERACTION_PAIRS:
                    continue
                i_c, label, itype = INTERACTION_PAIRS[key]
                p_d = 1.0 if distance == 1 else 0.5
                bpv_a = BPV.get(word[idx_a], 0)
                bpv_b = BPV.get(word[idx_b], 0)
                pair_score = (bpv_a + bpv_b) * i_c * p_d
                interactions.append(InteractionEvent(
                    word=word, pair=f"{word[idx_a]}+{word[idx_b]}",
                    label=label, interaction_type=itype,
                    i_c=i_c, p_d=p_d, score=pair_score,
                ))
                if idx_a not in consumed:
                    consumed[idx_a] = pair_score / 2
                if idx_b not in consumed:
                    consumed[idx_b] = pair_score / 2

        # ── Rules 1–3: Standard positional scoring ────────────────────
        word_score = sum(consumed.values())
        last_idx = n - 1
        for pos, ch in enumerate(word):
            if pos in consumed or ch not in BPV:
                continue
            word_score += BPV[ch] * self._pos_mult(pos, last_idx, ch)

        # ── Rule 3: Visual Complexity Anchor ─────────────────────────
        has_visual = any(ch in _VISUAL_COMPLEXITY for ch in word)
        if has_visual:
            word_score *= 1.2

        return word_score, interactions, doubles, has_visual

    # ------------------------------------------------------------------
    # Standardization: MicroScore → MicroResult
    # ------------------------------------------------------------------

    def _to_result(self, score: MicroScore, extra_raw: Dict = None) -> MicroResult:
        """Convert internal MicroScore to the canonical six-vector MicroResult."""
        lt = score.letter_totals
        total_bpv = max(1.0, sum(lt.values()))

        vectors = {
            "intensity":  score.raw_score / score.total_chars,
            "anxiety":    (lt.get("S", 0.0) + lt.get("N", 0.0)) / total_bpv * 100,
            "attention":  (lt.get("A", 0.0) + lt.get("K", 0.0)) / total_bpv * 100,
            "emotion":    (lt.get("M", 0.0) + lt.get("W", 0.0)) / total_bpv * 100,
            "agitation":  (lt.get("R", 0.0) + lt.get("Z", 0.0)) / total_bpv * 100,
            "complexity": float(score.words_with_visual_complexity),
        }

        raw = {
            "raw_score": score.raw_score,
            "letter_totals": score.letter_totals,
            "words_with_visual_complexity": score.words_with_visual_complexity,
            "interaction_events": [
                {
                    "word": e.word, "pair": e.pair, "label": e.label,
                    "type": e.interaction_type, "i_c": e.i_c,
                    "p_d": e.p_d, "score": round(e.score, 4),
                }
                for e in score.interaction_events
            ],
            "double_letter_events": [
                {"word": e.word, "pair": e.pair, "gm": e.gm, "score": round(e.score, 4)}
                for e in score.double_letter_events
            ],
        }
        if extra_raw:
            raw.update(extra_raw)

        return MicroResult(vectors=vectors, raw=raw, language=self.language_code)
