"""
MODULE 1 — Rolling Window Tokenizer
Treats text as a time-series signal.

Slices raw text into overlapping windows (default: window_size=1000, stride=500).

Hard Reset Rule:
    If a structural boundary is detected (double newline or chapter heading),
    the window halts, scores that segment, flushes the buffer, and resets the
    counter to 0. No emotional "bleed" across structural boundaries.
"""

import re
from dataclasses import dataclass
from typing import Generator, List, Tuple

# Matches chapter/section headings at the start of a line
_HEADING_RE = re.compile(
    r"^(?:chapter|section|part|prologue|epilogue|\d+\.)\s+",
    re.IGNORECASE | re.MULTILINE,
)

# Structural boundary: two or more consecutive newlines
_BOUNDARY_RE = re.compile(r"\n{2,}")


@dataclass
class TextWindow:
    """A single analysis window extracted from the source text."""

    index: int
    text: str
    start_char: int   # absolute offset into original text
    end_char: int     # absolute offset into original text
    reset_reason: str = "stride"  # "stride" | "structural_boundary"


class RollingWindowTokenizer:
    """
    Converts a raw text string into a sequence of TextWindow objects.

    Structural boundaries (\\n\\n or headings) trigger a hard reset:
    the current segment is emitted as-is and the sliding window starts
    fresh on the next segment. This prevents psychological signal from
    one section bleeding into another.
    """

    def __init__(self, window_size: int = 1000, stride: int = 500):
        if stride >= window_size:
            raise ValueError("stride must be smaller than window_size to produce overlapping windows")
        self.window_size = window_size
        self.stride = stride

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self, text: str) -> List[TextWindow]:
        """Return all windows produced from *text*."""
        windows: List[TextWindow] = []
        global_idx = 0

        for seg_text, seg_offset, boundary_type in self._split_on_boundaries(text):
            for win in self._slide(seg_text, seg_offset, global_idx, boundary_type):
                windows.append(win)
                global_idx += 1

        return windows

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_on_boundaries(
        self, text: str
    ) -> List[Tuple[str, int, str]]:
        """
        Split *text* into (segment_text, offset, boundary_type) tuples.

        Boundary types:
            "double_newline" — paragraph break
            "heading"        — chapter / section marker
            "eof"            — natural end of text
        """
        # Collect all boundary start positions
        boundary_positions: List[Tuple[int, int, str]] = []

        for m in _BOUNDARY_RE.finditer(text):
            boundary_positions.append((m.start(), m.end(), "double_newline"))

        for m in _HEADING_RE.finditer(text):
            # A heading itself starts a new segment; the boundary is just before it
            boundary_positions.append((m.start(), m.start(), "heading"))

        # Sort by position; if a heading falls inside a double-newline span, deduplicate
        boundary_positions.sort(key=lambda x: x[0])

        segments: List[Tuple[str, int, str]] = []
        prev_end = 0

        for b_start, b_end, b_type in boundary_positions:
            if b_start <= prev_end:
                # Overlapping boundary — skip to avoid empty segments
                continue
            segment = text[prev_end:b_start]
            if segment.strip():
                segments.append((segment, prev_end, b_type))
            prev_end = b_end

        # Trailing segment after the last boundary
        tail = text[prev_end:]
        if tail.strip():
            segments.append((tail, prev_end, "eof"))

        return segments

    def _slide(
        self,
        text: str,
        offset: int,
        start_idx: int,
        boundary_type: str,
    ) -> Generator[TextWindow, None, None]:
        """
        Yield overlapping windows from a single flat segment.

        The first window of every non-eof segment records the boundary trigger
        so downstream analysis can annotate the hard reset.
        """
        pos = 0
        idx = start_idx
        text_len = len(text)

        while pos < text_len:
            end = min(pos + self.window_size, text_len)
            chunk = text[pos:end]

            if chunk.strip():
                # Only the very first chunk of a boundary-triggered segment
                # carries the reset label; subsequent chunks are regular strides.
                reason = (
                    "structural_boundary"
                    if pos == 0 and boundary_type != "eof"
                    else "stride"
                )
                yield TextWindow(
                    index=idx,
                    text=chunk,
                    start_char=offset + pos,
                    end_char=offset + end,
                    reset_reason=reason,
                )
                idx += 1

            if end >= text_len:
                break

            pos += self.stride
