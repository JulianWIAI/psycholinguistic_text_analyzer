"""
Base Micro-Layer Analyzer
Defines MicroResult — the standardized signal envelope consumed by the
dissonance engine — and BaseMicroAnalyzer — the ABC every language-specific
micro analyzer must implement.

Canonical vector space (all languages resolve to these six keys):
    intensity   — overall orthographic / logographic signal strength
    anxiety     — nervousness / tension markers (S, N / hiragana heaviness)
    attention   — ego / focus / stress markers (A, K / kanji density)
    emotion     — emotional load (M, W / hiragana ratio)
    agitation   — restlessness / foreignness (R, Z / katakana ratio)
    complexity  — cognitive / visual / stroke complexity (W, M, K / stroke density)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

# The six canonical micro-layer dimensions shared across all languages.
MICRO_VECTOR_KEYS: tuple = (
    "intensity",
    "anxiety",
    "attention",
    "emotion",
    "agitation",
    "complexity",
)


@dataclass
class MicroResult:
    """
    Standardized output from any language-specific micro analyzer.

    vectors  — the six-dimensional signal dict (cross-language comparable)
    raw      — language-specific data preserved for UI and audit inspection
    language — ISO 639-1 code of the analyzer that produced this result
    """

    vectors: Dict[str, float] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)
    language: str = "EN"

    def get(self, key: str, default: float = 0.0) -> float:
        return self.vectors.get(key, default)

    def filled_vectors(self) -> Dict[str, float]:
        """Return the full six-key dict, padding missing keys with 0.0."""
        return {k: self.vectors.get(k, 0.0) for k in MICRO_VECTOR_KEYS}


class BaseMicroAnalyzer(ABC):
    """
    Contract for all language micro analyzers.

    The public analyze() method MUST return a MicroResult whose `vectors`
    dict contains all six canonical keys (absent keys default to 0.0 in
    the dissonance engine via filled_vectors()).
    """

    @property
    @abstractmethod
    def language_code(self) -> str:
        """ISO 639-1 language code this analyzer handles (e.g. "EN", "JA")."""
        ...

    @abstractmethod
    def analyze(self, text: str) -> MicroResult:
        """Analyze *text* and return a standardized MicroResult."""
        ...
