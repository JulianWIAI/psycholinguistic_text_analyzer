"""
MODULE 2-DE — German Micro-Layer Override
Extends the Latin BPV analyzer with German phonological normalisation.

Pre-processing applied before the standard BPV pipeline:
    Umlaut expansion : ä→ae  ö→oe  ü→ue  (Ä→AE  Ö→OE  Ü→UE)
    Eszett expansion : ß→ss  (double sibilant → standard Gm 1.8 via default rules)

After normalisation the full English pipeline runs unchanged, so all
interaction coefficients, visual complexity anchors, and positional
multipliers apply to the expanded Latin form.
"""

import re

from micro_layer.orthographic_analyzer import OrthographicAnalyzer
from micro_layer.base_analyzer import MicroResult

_UMLAUT_TABLE = str.maketrans("äöüÄÖÜ", "??????")  # placeholder; we use replace below

_REPLACEMENTS = [
    ("ä", "ae"), ("ö", "oe"), ("ü", "ue"),
    ("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE"),
    ("ß", "ss"),
]


def _normalise_german(text: str) -> str:
    for src, dst in _REPLACEMENTS:
        text = text.replace(src, dst)
    return text


class GermanOrthographicAnalyzer(OrthographicAnalyzer):
    """
    German orthographic analyzer.
    Inherits the full Latin BPV pipeline; pre-processes umlauts and ß
    so every character maps cleanly into the existing BPV table.
    """

    # Extend the word regex to capture umlaut characters before normalisation
    _WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")

    @property
    def language_code(self) -> str:
        return "DE"

    def analyze(self, text: str) -> MicroResult:
        normalised = _normalise_german(text)
        score = self._score(normalised)
        return self._to_result(score)
