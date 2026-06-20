"""
MODULE — Arabic (AR) and Farsi (FA) Micro-Layer Analyzers
Wraps psycho_core.analyze_ar() / analyze_fa() behind the BaseMicroAnalyzer interface.

Split-Stream behavior
---------------------
Stream A  raw RTL text — passed untouched by the caller (routes.py) to the
          steganography scanner, punctuation waveform builder, and UI rendering.

Stream B  sanitize_abjad(text) — Markdown, Latin structural noise, and Arabic
          diacritics (harakat) stripped before the sanitized payload reaches the
          C++ BPV engine and the spaCy entropy pipeline.

          Critical preservations:
            ، (U+060C) Arabic Comma      — sentence-boundary signal for spaCy
            ؟ (U+061F) Arabic Question   — sentence-boundary signal for spaCy
            Arabic letters and spaces     — the actual BPV payload

RTL note
--------
The C++ engine receives the text in logical order (the byte sequence as stored
in memory, which is the keystroke sequence).  No reversal is applied here.
spaCy Arabic models also operate on logical order.

subprocess bridge
-----------------
If a path to a compiled standalone binary is supplied at construction time,
the analyzer pipes Stream B via stdin with --lang=AR or --lang=FA.
"""

import re
import subprocess
from typing import Optional

from micro_layer.base_analyzer import BaseMicroAnalyzer, MicroResult

# ---------------------------------------------------------------------------
# Stream B — Abjad sanitizer (pre-compiled, zero per-call overhead)
#
# Pipeline order is load-bearing (mirrors sanitize_ru):
#   1–4. Remove code/Markdown structure (fences, inline code, HR, MD prefixes).
#   5.   Strip Latin tokens — structural noise in Arabic/Farsi intercepts.
#   6.   Strip Arabic diacritics (harakat U+064B–U+065F, tatweel U+0640) —
#        these are voweling annotations; the BPV model operates on consonants.
#   7.   Normalize inline whitespace before period injection.
#   8.   Period injection — must fire while \n boundaries still exist.
#   9.   Final whitespace collapse.
#
# Arabic-specific punctuation PRESERVED throughout:
#   ، (U+060C) — Arabic comma (magnitude-1 pause; spaCy sentence boundary)
#   ؟ (U+061F) — Arabic question mark (magnitude-4 pause; sentence boundary)
# ---------------------------------------------------------------------------

_RE_FENCE      = re.compile(r"```.*?```", re.DOTALL)
_RE_INLINE     = re.compile(r"`[^`\n]+`")
_RE_HR         = re.compile(r"^[ \t]*[-*=]{3,}[ \t]*$", re.MULTILINE)
_RE_MD_PFX     = re.compile(r"^[ \t]*(?:#{1,6}|[*\->|]|=>)[ \t]*", re.MULTILINE)
_RE_LATIN      = re.compile(r"[A-Za-z]+")

# Arabic diacritics (harakat) U+064B–U+065F + tatweel U+0640
# Also strip U+0610–U+061A (extended Arabic marks) and U+0670 (superscript Alef)
_RE_DIACRITICS = re.compile(
    r"[ؐ-ؚـً-ٰٟۖ-ۜ۟-ۤۧ-۪ۨ-ۭ]"
)

_RE_INLINE_WS  = re.compile(r"[^\S\n]+")
# Period injection: close unpunctuated lines (Arabic text uses ، for comma
# and ؟ for question mark; fall back to ASCII period for sentence closure)
_RE_PERIOD     = re.compile(r"([^\s.!?،؟])[ \t]*$", re.MULTILINE)
_RE_WS_FLAT    = re.compile(r"\s+")


def sanitize_abjad(text: str) -> str:
    """
    Return a sanitized Arabic/Farsi prose string (Stream B).

    Preserves Arabic comma ، and Arabic question mark ؟ as sentence
    boundary anchors for spaCy and the Burstiness calculator.
    Strips diacritics (harakat) since the BPV engine is consonant-only.
    """
    s = _RE_FENCE.sub(" ", text)
    s = _RE_INLINE.sub(" ", s)
    s = _RE_HR.sub(" ", s)
    s = _RE_MD_PFX.sub("", s)
    s = _RE_LATIN.sub(" ", s)
    s = _RE_DIACRITICS.sub("", s)
    s = _RE_INLINE_WS.sub(" ", s)
    s = _RE_PERIOD.sub(r"\1.", s)
    s = _RE_WS_FLAT.sub(" ", s)
    return s.strip()


# ---------------------------------------------------------------------------
# C++ binding availability
# ---------------------------------------------------------------------------

try:
    import psycho_core as _core
    _HAVE_AR = hasattr(_core, "analyze_ar")
    _HAVE_FA = hasattr(_core, "analyze_fa")
except ImportError:
    _core    = None          # type: ignore[assignment]
    _HAVE_AR = False
    _HAVE_FA = False


# ---------------------------------------------------------------------------
# Shared window-list → MicroResult parser (identical to ru_analyzer._parse_windows)
# ---------------------------------------------------------------------------

def _parse_windows(raw_windows: list) -> MicroResult:
    if not raw_windows:
        return MicroResult(
            vectors={
                "intensity": 0.0, "anxiety": 0.0, "attention": 0.0,
                "emotion":   0.0, "agitation": 0.0, "complexity": 0.0,
            },
            raw={},
        )

    keys = ("intensity", "anxiety", "attention", "emotion", "agitation", "complexity")
    agg  = {k: 0.0 for k in keys}

    for win in raw_windows:
        vecs = win.get("vectors", {})
        for k in keys:
            agg[k] += vecs.get(k, 0.0)

    n       = max(1, len(raw_windows))
    vectors = {k: v / n for k, v in agg.items()}
    raw     = raw_windows[0].get("raw_telemetry", {})

    return MicroResult(vectors=vectors, raw=raw)


# ---------------------------------------------------------------------------
# Arabic Analyzer
# ---------------------------------------------------------------------------

class ArabicOrthographicAnalyzer(BaseMicroAnalyzer):
    """
    Arabic (AR) Abjad BPV analyzer.
    Routes sanitized Stream B to psycho_core.analyze_ar() (28-bin matrix)
    or to a compiled standalone binary via subprocess with --lang=AR.
    """

    @property
    def language_code(self) -> str:
        return "AR"

    def __init__(self, cpp_binary: Optional[str] = None) -> None:
        self._cpp_binary = cpp_binary

    def analyze(
        self,
        text: str,
        window_size: int = 1000,
        stride: int = 500,
    ) -> MicroResult:
        clean = sanitize_abjad(text)

        if _HAVE_AR and self._cpp_binary is None:
            raw_windows = _core.analyze_ar(clean, window_size, stride)
        elif self._cpp_binary is not None:
            raw_windows = self._subprocess_analyze(clean, window_size, stride, "--lang=AR")
        else:
            from micro_layer.orthographic_analyzer import OrthographicAnalyzer
            return OrthographicAnalyzer().analyze(clean)

        return _parse_windows(raw_windows)

    def _subprocess_analyze(
        self,
        sanitized_text: str,
        window_size: int,
        stride: int,
        lang_flag: str,
    ) -> list:
        import json
        proc = subprocess.run(
            [self._cpp_binary, lang_flag,
             f"--window={window_size}", f"--stride={stride}"],
            input=sanitized_text,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"psycho_core binary exited {proc.returncode}: {proc.stderr.strip()}"
            )
        return json.loads(proc.stdout)


# ---------------------------------------------------------------------------
# Farsi Analyzer
# ---------------------------------------------------------------------------

class FarsiOrthographicAnalyzer(BaseMicroAnalyzer):
    """
    Farsi (FA) Abjad BPV analyzer.
    Routes sanitized Stream B to psycho_core.analyze_fa() (32-bin matrix:
    28 Arabic + پ چ ژ گ) or to a compiled binary with --lang=FA.
    """

    @property
    def language_code(self) -> str:
        return "FA"

    def __init__(self, cpp_binary: Optional[str] = None) -> None:
        self._cpp_binary = cpp_binary

    def analyze(
        self,
        text: str,
        window_size: int = 1000,
        stride: int = 500,
    ) -> MicroResult:
        clean = sanitize_abjad(text)

        if _HAVE_FA and self._cpp_binary is None:
            raw_windows = _core.analyze_fa(clean, window_size, stride)
        elif self._cpp_binary is not None:
            raw_windows = self._subprocess_analyze(clean, window_size, stride, "--lang=FA")
        else:
            from micro_layer.orthographic_analyzer import OrthographicAnalyzer
            return OrthographicAnalyzer().analyze(clean)

        return _parse_windows(raw_windows)

    def _subprocess_analyze(
        self,
        sanitized_text: str,
        window_size: int,
        stride: int,
        lang_flag: str,
    ) -> list:
        import json
        proc = subprocess.run(
            [self._cpp_binary, lang_flag,
             f"--window={window_size}", f"--stride={stride}"],
            input=sanitized_text,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"psycho_core binary exited {proc.returncode}: {proc.stderr.strip()}"
            )
        return json.loads(proc.stdout)
