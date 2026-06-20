"""
MODULE 2-CPP — C++ Micro-Layer Adapter
Wraps the compiled psycho_core pybind11 module behind the BaseMicroAnalyzer
interface. Falls back to a supplied Python analyzer when psycho_core has not
been compiled.

Compatible languages:
    EN — standard BPV pipeline, no pre-processing needed.
    DE — BPV pipeline after umlaut/ß normalization; pass preprocess=_normalise_german
         and fallback=GermanOrthographicAnalyzer().

ES and FR override _double_gm() / _pos_mult() with rules the C++ module does
not expose, so they continue to use their Python analyzers.
JA uses a completely different logographic pipeline.
"""

import warnings
from typing import Callable, Optional

from micro_layer.base_analyzer import BaseMicroAnalyzer, MicroResult

try:
    import psycho_core as _core
    _CPP_AVAILABLE = True
except ImportError:
    _core = None
    _CPP_AVAILABLE = False


class CppOrthographicAnalyzer(BaseMicroAnalyzer):
    """
    BPV orthographic analyzer backed by the compiled C++ psycho_core module.

    Parameters
    ----------
    language_code : str
        ISO code returned by the language_code property ("EN" or "DE").
    preprocess : callable, optional
        Text transformation applied before C++ scoring (umlaut expansion
        for German).  Identity function if omitted.
    fallback : BaseMicroAnalyzer, optional
        Analyzer to use when psycho_core is not compiled.  Defaults to
        OrthographicAnalyzer() (English).  Pass GermanOrthographicAnalyzer()
        when language_code is "DE" so the Python fallback preserves German
        phonological rules.
    """

    def __init__(
        self,
        language_code: str = "EN",
        preprocess: Optional[Callable[[str], str]] = None,
        fallback: Optional[BaseMicroAnalyzer] = None,
    ):
        self._lang = language_code
        self._pre  = preprocess or (lambda t: t)

        if not _CPP_AVAILABLE:
            warnings.warn(
                "psycho_core C++ module not found — falling back to Python analyzer. "
                "Build with:\n"
                "  cd cpp_core && cmake -B build -DCMAKE_BUILD_TYPE=Release "
                "&& cmake --build build --config Release",
                RuntimeWarning,
                stacklevel=2,
            )
            if fallback is not None:
                self._fallback = fallback
            else:
                from micro_layer.orthographic_analyzer import OrthographicAnalyzer
                self._fallback = OrthographicAnalyzer()
        else:
            self._fallback = None

    @property
    def language_code(self) -> str:
        return self._lang

    def analyze(self, text: str) -> MicroResult:
        if self._fallback is not None:
            return self._fallback.analyze(text)

        processed = self._pre(text)

        if not processed.strip():
            return MicroResult(
                vectors={
                    "intensity": 0.0, "anxiety": 0.0, "attention": 0.0,
                    "emotion":   0.0, "agitation": 0.0, "complexity": 0.0,
                },
                raw={},
                language=self._lang,
            )

        # window_size > len(text) → C++ engine produces exactly one window
        # covering the entire input; stride=1 satisfies stride < window_size.
        n       = len(processed) + 1
        results = _core.analyze(processed, n, 1)

        if not results:
            return MicroResult(
                vectors={
                    "intensity": 0.0, "anxiety": 0.0, "attention": 0.0,
                    "emotion":   0.0, "agitation": 0.0, "complexity": 0.0,
                },
                raw={},
                language=self._lang,
            )

        win = results[0]
        rt  = win.get("raw_telemetry", {})

        return MicroResult(
            vectors=dict(win["vectors"]),
            raw={
                "total_chars":             rt.get("total_chars", 0),
                "total_words":             rt.get("total_words", 0),
                "avg_word_length":         rt.get("avg_word_length", 0.0),
                "top_micro_chars":         rt.get("top_micro_chars", {}),
                "double_letter_anomalies": rt.get("double_letter_anomalies", {}),
                # v3.3 — steganographic anomaly detection
                "hidden_unicode_count":    rt.get("hidden_unicode_count", 0),
                "stego_anomaly_flag":      rt.get("stego_anomaly_flag", False),
                # v3.3 — punctuation structural waveform
                "punctuation_waveform":    rt.get("punctuation_waveform", []),
            },
            language=self._lang,
        )
