"""
Korean (KO) Micro-Layer Orthographic Analyzer

Split-Stream behavior
---------------------
Stream A  raw Hangul text — passed untouched by the caller (routes.py) to the
          steganography scanner, punctuation waveform, and UI rendering.

Stream B  sanitize_ko(text) → unpack_hangul_to_jamo() — structural noise stripped,
          syllable blocks decomposed into conjoining Jamo before the C++ BPV engine.

Hangul syllable decomposition formula:
    idx     = cp - 0xAC00
    onset   = idx // (21 * 28)      → chr(U+1100 + onset)
    nucleus = (idx % (21*28)) // 28  → chr(U+1161 + nucleus)
    coda    = idx % 28               → chr(U+11A7 + coda) if coda > 0

total_chars is overridden with native syllable count after C++ analysis because
Jamo decomposition inflates the character count by ~2–3×.
"""

import re
from typing import Optional

from micro_layer.base_analyzer import BaseMicroAnalyzer, MicroResult

# ---------------------------------------------------------------------------
# Hangul decomposition constants
# ---------------------------------------------------------------------------
_SYLLABLE_START = 0xAC00
_SYLLABLE_END   = 0xD7A3
_ONSET_BASE     = 0x1100
_NUCLEUS_BASE   = 0x1161
_CODA_BASE      = 0x11A7   # coda index 0 = no coda; coda 1 → U+11A8

_NUM_NUCLEUS = 21
_NUM_CODA    = 28


def unpack_hangul_to_jamo(text: str) -> str:
    """
    Decompose all Hangul syllable blocks (U+AC00–U+D7A3) in *text* into
    constituent conjoining Jamo. Non-Hangul characters are preserved as-is.

    Output Jamo ranges:
      Onset   U+1100–U+1112  (19 basic initials)
      Nucleus U+1161–U+1175  (21 vowels)
      Coda    U+11A8–U+11C2  (27 codas; absent when coda index == 0)
    """
    out = []
    for ch in text:
        cp = ord(ch)
        if _SYLLABLE_START <= cp <= _SYLLABLE_END:
            idx     = cp - _SYLLABLE_START
            onset   = idx // (_NUM_NUCLEUS * _NUM_CODA)
            nucleus = (idx % (_NUM_NUCLEUS * _NUM_CODA)) // _NUM_CODA
            coda    = idx % _NUM_CODA
            out.append(chr(_ONSET_BASE + onset))
            out.append(chr(_NUCLEUS_BASE + nucleus))
            if coda > 0:
                out.append(chr(_CODA_BASE + coda))
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# Stream B sanitizer
# ---------------------------------------------------------------------------

# 1. Fenced code blocks
_RE_FENCE     = re.compile(r"```.*?```", re.DOTALL)
# 2. Inline code
_RE_INLINE    = re.compile(r"`[^`\n]+`")
# 3. Markdown structural prefixes
_RE_MD_PFX    = re.compile(r"^[ \t]*(?:#{1,6}|[*\->|])[ \t]*", re.MULTILINE)
# 4. Latin tokens (noise in Korean intercepts)
_RE_LATIN     = re.compile(r"[A-Za-z]+")
# 5. Non-Korean non-punctuation (remove Chinese chars, Arabic, etc.)
_RE_NON_KO    = re.compile(r"[^가-힣ᄀ-ᇿ㄰-㆏\s.,!?]")
# 6. Collapse inline whitespace (preserve newlines for period injection)
_RE_INLINE_WS = re.compile(r"[^\S\n]+")
# 7. Period injection for bare line-ends
_RE_PERIOD    = re.compile(r"([^\s.!?])[ \t]*$", re.MULTILINE)
# 8. Final whitespace collapse
_RE_WS_FLAT   = re.compile(r"\s+")


def sanitize_ko(text: str) -> str:
    """
    Return a sanitized Korean prose string (Stream B).

    Pipeline order:
      1–3. Remove code/Markdown structure.
      4.   Strip Latin tokens.
      5.   Remove non-Korean, non-punctuation codepoints.
      6.   Normalize inline whitespace.
      7.   Period injection (while \\n boundaries exist).
      8.   Final collapse → space-delimited syllabic words.
    """
    s = _RE_FENCE.sub(" ", text)
    s = _RE_INLINE.sub(" ", s)
    s = _RE_MD_PFX.sub("", s)
    s = _RE_LATIN.sub(" ", s)
    s = _RE_NON_KO.sub(" ", s)
    s = _RE_INLINE_WS.sub(" ", s)
    s = _RE_PERIOD.sub(r"\1.", s)
    s = _RE_WS_FLAT.sub(" ", s)
    return s.strip()


# ---------------------------------------------------------------------------
# C++ binding
# ---------------------------------------------------------------------------
try:
    import psycho_core as _core
    _HAVE_CORE = hasattr(_core, "analyze_ko")
except ImportError:
    _core = None        # type: ignore[assignment]
    _HAVE_CORE = False


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class KoreanOrthographicAnalyzer(BaseMicroAnalyzer):
    """
    Korean BPV analyzer — routes Jamo-decomposed Stream B to psycho_core.analyze_ko().

    total_chars in raw_telemetry is overridden with the native syllable count of
    the original text so the UI displays meaningful word-unit counts rather than
    the inflated Jamo character count produced by decomposition.
    """

    @property
    def language_code(self) -> str:
        return "KO"

    def __init__(self) -> None:
        pass

    def analyze(
        self,
        text: str,
        window_size: int = 1000,
        stride: int = 500,
    ) -> MicroResult:
        # Count native syllables from the original text (before sanitization)
        syllable_count = sum(
            1 for ch in text
            if _SYLLABLE_START <= ord(ch) <= _SYLLABLE_END
        )

        # Stream B: sanitize → Jamo decompose
        jamo_text = unpack_hangul_to_jamo(sanitize_ko(text))

        if _HAVE_CORE:
            raw_windows = _core.analyze_ko(jamo_text, window_size, stride)
        else:
            # Fallback: return zero vectors when C++ module not compiled yet
            return MicroResult(
                vectors={
                    "intensity": 0.0, "anxiety": 0.0, "attention": 0.0,
                    "emotion":   0.0, "agitation": 0.0, "complexity": 0.0,
                },
                raw={},
                language="KO",
            )

        return self._parse_windows(raw_windows, syllable_count)

    # ------------------------------------------------------------------
    # Window list → MicroResult
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_windows(raw_windows: list, syllable_count: int) -> MicroResult:
        if not raw_windows:
            return MicroResult(
                vectors={
                    "intensity": 0.0, "anxiety": 0.0, "attention": 0.0,
                    "emotion":   0.0, "agitation": 0.0, "complexity": 0.0,
                },
                raw={},
                language="KO",
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

        # Override jamo count with native syllable count
        if syllable_count > 0:
            raw["total_chars"] = syllable_count

        return MicroResult(vectors=vectors, raw=raw, language="KO")
