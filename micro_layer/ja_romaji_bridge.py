"""
micro_layer/ja_romaji_bridge.py — Japanese → Romaji conversion bridge.

Converts Kanji / Kana text to Hepburn romanisation using pykakasi so that
the A–Z physics engine can compute numeric letter values, FFT, and σ for
Japanese text (measured on its phonetic waveform rather than its logographic
representation).

Usage
-----
    from micro_layer.ja_romaji_bridge import to_romaji, is_available

    romaji = to_romaji("テキスト分析")   # → "tekisuto bunseki"

If pykakasi is not installed the function returns the original text unchanged
and ``is_available()`` returns False.  Install:
    pip install pykakasi
"""

import warnings
from typing import Optional

# ── Optional dependency ───────────────────────────────────────────────────────
_kakasi_instance = None
_AVAILABLE: bool = False

try:
    import pykakasi as _pykakasi
    _kakasi_instance = _pykakasi.kakasi()
    _AVAILABLE = True
except ImportError:
    warnings.warn(
        "pykakasi not installed — Japanese Romaji bridge disabled. "
        "Install with: pip install pykakasi",
        RuntimeWarning,
        stacklevel=1,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def is_available() -> bool:
    """Return True if pykakasi is installed and the bridge is functional."""
    return _AVAILABLE


def to_romaji(text: str) -> str:
    """
    Convert a Japanese string to Hepburn romanisation.

    Each converted segment contributes its 'hepburn' form (Latin letters only).
    Segments that cannot be romanised (e.g. punctuation, numbers) are replaced
    by a space so that they do not disrupt word tokenisation downstream.

    Parameters
    ----------
    text : str
        Input text containing Kanji, Hiragana, Katakana, or mixed script.

    Returns
    -------
    str
        Romanised string (lowercase Latin).  If pykakasi is unavailable, the
        original *text* is returned unchanged.
    """
    if not _AVAILABLE or _kakasi_instance is None:
        return text

    try:
        result = _kakasi_instance.convert(text)
    except Exception:
        return text

    parts = []
    for item in result:
        # 'hepburn' key contains the romanised form; fall back to 'orig'
        roman = item.get("hepburn") or item.get("orig") or ""
        # Keep only ASCII letter characters to feed the BPV/somatic engine
        cleaned = "".join(ch for ch in roman if ch.isalpha() and ord(ch) < 128)
        if cleaned:
            parts.append(cleaned)

    return " ".join(parts) if parts else text
