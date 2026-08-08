"""
Literary Layer — Line Index
Converts absolute char offsets into 1-based line numbers in O(log n).

Build the index once per document before the window loop, then pass the
same list into every per-window literary analyzer call.

    index = build_line_index(full_document_text)   # once
    line  = char_to_line(char_position, index)     # per finding
"""
from __future__ import annotations

import bisect
from typing import List


def build_line_index(text: str) -> List[int]:
    """
    Return a sorted list of char offsets at which each line begins.

    index[0] is always 0 (the document start).  A newline at position i
    starts a new line at i + 1, so index[-1] is the start of the final line.

    Example:
        "ab\\ncd\\nef"  →  [0, 3, 6]
        char 0..2 → line 1, char 3..5 → line 2, char 6..7 → line 3
    """
    offsets: List[int] = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def char_to_line(char_pos: int, index: List[int]) -> int:
    """
    Return the 1-based line number for *char_pos* using a pre-built line index.

    bisect_right(index, char_pos) naturally produces 1-based output because
    index[0] == 0: a char at position 0 yields bisect_right([0, …], 0) == 1.
    """
    return bisect.bisect_right(index, char_pos)
