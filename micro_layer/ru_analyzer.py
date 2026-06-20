"""
MODULE — Russian (Cyrillic) Micro-Layer Analyzer
Wraps psycho_core.analyze_ru() behind the BaseMicroAnalyzer interface.

Split-Stream behavior
---------------------
Stream A  raw text — passed untouched by the caller (routes.py) to the
          steganography scanner, punctuation waveform, and UI rendering.

Stream B  sanitize_ru(text) — Markdown and Latin structural noise stripped
          before the sanitized payload reaches the C++ BPV engine and the
          spaCy entropy pipeline.  Russian punctuation is preserved so the
          Structural Morse tracker (build_punct_waveform) still fires on it.

subprocess bridge
-----------------
If a path to a compiled standalone binary is supplied at construction time,
the analyzer pipes Stream B via stdin with --lang=RU rather than calling the
pybind11 module directly.  The pybind11 path is the default and preferred mode.
"""

import re
import subprocess
from typing import Optional

from micro_layer.base_analyzer import BaseMicroAnalyzer, MicroResult

# ---------------------------------------------------------------------------
# Stream B — Cyrillic sanitizer (pre-compiled, zero per-call overhead)
# ---------------------------------------------------------------------------

# 1. Fenced code blocks (``` ... ```) — technical Latin jargon
_RE_FENCE      = re.compile(r"```.*?```", re.DOTALL)
# 2. Inline code (`...`)
_RE_INLINE     = re.compile(r"`[^`\n]+`")
# 3. Horizontal rules (--- / *** / ===)
_RE_HR         = re.compile(r"^[ \t]*[-*=]{3,}[ \t]*$", re.MULTILINE)
# 4. Markdown structural line prefixes (# ## * - > => |)
_RE_MD_PFX     = re.compile(r"^[ \t]*(?:#{1,6}|[*\->|]|=>)[ \t]*", re.MULTILINE)
# 5. Latin-alphabet tokens — structural noise in Cyrillic intercepts.
#    Removed AFTER prefix stripping so Latin headers don't leave orphan symbols.
_RE_LATIN      = re.compile(r"[A-Za-z]+")
# 6. Collapse inline whitespace (spaces/tabs) without consuming newlines —
#    newlines must survive for step 7 (period injection anchors to $).
_RE_INLINE_WS  = re.compile(r"[^\S\n]+")
# 7. Period injection — close unpunctuated lines before flattening.
#    Captures the last non-whitespace non-terminal char on each line.
_RE_PERIOD     = re.compile(r"([^\s.!?])[ \t]*$", re.MULTILINE)
# 8. Final whitespace collapse — all remaining whitespace (including \n) → space.
_RE_WS_FLAT    = re.compile(r"\s+")


def sanitize_ru(text: str) -> str:
    """
    Return a sanitized Cyrillic prose string (Stream B).

    The original *text* (Stream A) is never modified.

    Pipeline order is load-bearing:
      1–4. Remove code/Markdown structure before Latin stripping so headers
           don't leave floating punctuation.
      5.   Strip Latin tokens — removes code identifiers, mixed-script noise.
      6.   Normalize inline whitespace before period injection.
      7.   Period injection — must fire while \\n boundaries still exist.
      8.   Final collapse — newlines converted to spaces for spaCy sentence flow.
    """
    s = _RE_FENCE.sub(" ", text)
    s = _RE_INLINE.sub(" ", s)
    s = _RE_HR.sub(" ", s)
    s = _RE_MD_PFX.sub("", s)
    s = _RE_LATIN.sub(" ", s)
    s = _RE_INLINE_WS.sub(" ", s)
    s = _RE_PERIOD.sub(r"\1.", s)
    s = _RE_WS_FLAT.sub(" ", s)
    return s.strip()


# ---------------------------------------------------------------------------
# C++ binding availability check
# ---------------------------------------------------------------------------

try:
    import psycho_core as _core
    _HAVE_CORE = hasattr(_core, "analyze_ru")
except ImportError:
    _core = None          # type: ignore[assignment]
    _HAVE_CORE = False


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class RussianOrthographicAnalyzer(BaseMicroAnalyzer):
    """
    Cyrillic BPV analyzer — routes Stream B to psycho_core.analyze_ru()
    or, optionally, to a compiled standalone binary via subprocess.

    Parameters
    ----------
    cpp_binary : path to a standalone psycho_core CLI binary that reads from
                 stdin and accepts --lang=RU.  When None (default), the
                 pybind11 module is called directly.
    """

    @property
    def language_code(self) -> str:
        return "RU"

    def __init__(self, cpp_binary: Optional[str] = None) -> None:
        self._cpp_binary = cpp_binary

    def analyze(
        self,
        text: str,
        window_size: int = 1000,
        stride: int = 500,
    ) -> MicroResult:
        clean = sanitize_ru(text)   # Stream B — Markdown/Latin stripped

        if _HAVE_CORE and self._cpp_binary is None:
            raw_windows = _core.analyze_ru(clean, window_size, stride)
        elif self._cpp_binary is not None:
            raw_windows = self._subprocess_analyze(clean, window_size, stride)
        else:
            # Dev fallback: Python Latin engine on Stream B.
            # Produces a rough approximation — install psycho_core for accuracy.
            from micro_layer.orthographic_analyzer import OrthographicAnalyzer
            return OrthographicAnalyzer().analyze(clean)

        return self._parse_windows(raw_windows)

    # ------------------------------------------------------------------
    # subprocess bridge
    # ------------------------------------------------------------------

    def _subprocess_analyze(
        self,
        sanitized_text: str,
        window_size: int,
        stride: int,
    ) -> list:
        """
        Pipe sanitized Cyrillic payload to the compiled binary via stdin.
        Encoding is explicitly UTF-8 — critical for Cyrillic multibyte sequences.
        """
        import json

        proc = subprocess.run(
            [
                self._cpp_binary,
                "--lang=RU",
                f"--window={window_size}",
                f"--stride={stride}",
            ],
            input=sanitized_text,
            capture_output=True,
            encoding="utf-8",     # must not be left to locale default
            errors="replace",
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"psycho_core binary exited {proc.returncode}: "
                f"{proc.stderr.strip()}"
            )

        return json.loads(proc.stdout)

    # ------------------------------------------------------------------
    # Window list → MicroResult
    # ------------------------------------------------------------------

    @staticmethod
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
