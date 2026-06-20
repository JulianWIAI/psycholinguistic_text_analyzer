/**
 * window_engine.cpp
 * -----------------
 * Implementation of the zero-copy rolling window tokenizer.
 *
 * Key performance properties:
 *   - std::string_view is used throughout; no string copies are made for
 *     individual windows.  The entire document buffer is allocated once by
 *     the caller and every TextWindow::text points into it.
 *   - Boundary detection is a single linear scan: O(N) for N = document chars.
 *   - The sorted-merge step is O(B log B) for B = number of boundaries, which
 *     is negligible compared to the downstream BPV scoring.
 */

#include "window_engine.h"
#include <algorithm>
#include <cctype>
#include <cstring>

namespace psycho {

// ---------------------------------------------------------------------------
// UTF-8 helper — walk pos backward to the start of the current character.
// Continuation bytes are 10xxxxxx (0x80–0xBF); a leading byte is anything else.
// ---------------------------------------------------------------------------
static std::size_t utf8_char_start(std::string_view sv, std::size_t pos) noexcept {
    while (pos > 0 && (static_cast<unsigned char>(sv[pos]) & 0xC0) == 0x80)
        --pos;
    return pos;
}

// ---------------------------------------------------------------------------
// Heading keywords (all lowercase; compared case-insensitively in the scan).
// Matches Python: r"^(?:chapter|section|part|prologue|epilogue|\d+\.)\s+"
// ---------------------------------------------------------------------------
static constexpr const char* HEADING_KEYWORDS[] = {
    "chapter", "section", "part", "prologue", "epilogue"
};
static constexpr int N_HEADING_KEYWORDS =
    static_cast<int>(sizeof(HEADING_KEYWORDS) / sizeof(HEADING_KEYWORDS[0]));


// ===========================================================================
// RollingWindowEngine — constructor
// ===========================================================================

RollingWindowEngine::RollingWindowEngine(int window_size, int stride)
    : window_size_(window_size), stride_(stride)
{
    if (stride_ >= window_size_) {
        throw std::invalid_argument(
            "stride must be strictly less than window_size to produce overlapping windows"
        );
    }
}


// ===========================================================================
// Private static: build_line_index
// ===========================================================================

RollingWindowEngine::LineIndex
RollingWindowEngine::build_line_index(std::string_view text) {
    LineIndex starts;
    starts.push_back(0);          // line 1 always starts at offset 0
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '\n' && i + 1 < text.size()) {
            starts.push_back(i + 1);   // line N+1 starts after the '\n'
        }
    }
    return starts;
}

// ===========================================================================
// Private static: line_of
// ===========================================================================

int RollingWindowEngine::line_of(
    const LineIndex& idx,
    std::size_t      pos
) noexcept {
    // upper_bound gives the first element > pos;
    // its index equals the 1-based line number.
    const auto it = std::upper_bound(idx.begin(), idx.end(), pos);
    return static_cast<int>(it - idx.begin());
}


// ===========================================================================
// Public: tokenize
// ===========================================================================

std::vector<TextWindow> RollingWindowEngine::tokenize(std::string_view text) const {
    std::vector<TextWindow> out;
    int global_idx = 0;

    const LineIndex line_idx = build_line_index(text);   // O(N) pre-pass

    auto boundaries = find_boundaries(text);
    std::stable_sort(boundaries.begin(), boundaries.end(),
        [](const Boundary& a, const Boundary& b) { return a.b_start < b.b_start; });

    std::size_t prev_end = 0;
    for (const auto& b : boundaries) {
        if (b.b_start <= prev_end) continue;
        std::string_view seg = text.substr(prev_end, b.b_start - prev_end);
        if (!is_blank(seg)) {
            slide_segment(seg, prev_end, global_idx, true, line_idx, out);
        }
        prev_end = b.b_end;
    }

    if (prev_end < text.size()) {
        std::string_view tail = text.substr(prev_end);
        if (!is_blank(tail)) {
            slide_segment(tail, prev_end, global_idx, false, line_idx, out);
        }
    }

    return out;
}


// ===========================================================================
// Private: find_boundaries
// ===========================================================================

std::vector<RollingWindowEngine::Boundary>
RollingWindowEngine::find_boundaries(std::string_view text) const {
    std::vector<Boundary> result;
    const std::size_t n = text.size();

    std::size_t i = 0;
    while (i < n) {
        if (text[i] == '\n') {
            // Count run of consecutive newlines.
            std::size_t j = i;
            while (j < n && text[j] == '\n') ++j;

            if (j - i >= 2) {
                // Two or more newlines = paragraph boundary.
                result.push_back({ i, j, "double_newline" });
            }
            i = j;  // advance past all consumed newlines
        } else {
            // Check for a heading at the start of a line.
            bool at_line_start = (i == 0) || (text[i - 1] == '\n');
            if (at_line_start && is_heading_start(text, i)) {
                // The heading itself starts the next segment (b_end == b_start).
                result.push_back({ i, i, "heading" });
            }
            ++i;
        }
    }

    return result;
}


// ===========================================================================
// Private: is_heading_start
// ===========================================================================

bool RollingWindowEngine::is_heading_start(
    std::string_view text,
    std::size_t      pos
) const noexcept {
    const std::size_t remaining = text.size() - pos;

    // Pattern 1: digit(s) followed by '.' then whitespace  (e.g. "1. Title")
    if (remaining >= 2 && std::isdigit(static_cast<unsigned char>(text[pos]))) {
        std::size_t k = pos;
        while (k < text.size() && std::isdigit(static_cast<unsigned char>(text[k])))
            ++k;
        if (k < text.size() && text[k] == '.' &&
            k + 1 < text.size() &&
            std::isspace(static_cast<unsigned char>(text[k + 1]))) {
            return true;
        }
    }

    // Pattern 2: case-insensitive keyword match (chapter, section, …)
    for (int ki = 0; ki < N_HEADING_KEYWORDS; ++ki) {
        const char*  kw   = HEADING_KEYWORDS[ki];
        std::size_t  klen = std::strlen(kw);
        if (remaining < klen + 1) continue;

        bool match = true;
        for (std::size_t ci = 0; ci < klen; ++ci) {
            if (std::tolower(static_cast<unsigned char>(text[pos + ci])) != kw[ci]) {
                match = false;
                break;
            }
        }
        if (match && std::isspace(static_cast<unsigned char>(text[pos + klen]))) {
            return true;
        }
    }

    return false;
}


// ===========================================================================
// Private: slide_segment
// ===========================================================================

void RollingWindowEngine::slide_segment(
    std::string_view        seg,
    std::size_t             offset,
    int&                    global_idx,
    bool                    is_boundary_segment,
    const LineIndex&        line_idx,
    std::vector<TextWindow>& out
) const {
    int pos     = 0;
    int seg_len = static_cast<int>(seg.size());
    bool first  = true;  // only the first chunk of a boundary segment is labelled

    while (pos < seg_len) {
        int end = std::min(pos + window_size_, seg_len);
        // Snap end to a UTF-8 character boundary so multi-byte chars are never split.
        if (end < seg_len)
            end = static_cast<int>(utf8_char_start(seg, static_cast<std::size_t>(end)));

        std::string_view chunk = seg.substr(static_cast<std::size_t>(pos),
                                             static_cast<std::size_t>(end - pos));

        if (!is_blank(chunk)) {
            // Label: only the first chunk of a segment that was triggered by
            // a structural boundary carries "structural_boundary".
            // All other chunks (and the tail segment) get "stride".
            const bool is_reset_chunk = first && is_boundary_segment;
            const std::size_t abs_start = offset + static_cast<std::size_t>(pos);
            const std::size_t abs_end   = offset + static_cast<std::size_t>(end);

            out.push_back(TextWindow{
                .index        = global_idx++,
                .text         = chunk,
                .start_char   = abs_start,
                .end_char     = abs_end,
                .reset_reason = is_reset_chunk ? "structural_boundary" : "stride",
                .start_line   = line_of(line_idx, abs_start),
                .end_line     = line_of(line_idx, abs_end > 0 ? abs_end - 1 : abs_end),
            });
        }

        first = false;
        if (end >= seg_len) break;
        pos += stride_;
        // Align pos to a UTF-8 character start after stride advance.
        if (pos < seg_len)
            pos = static_cast<int>(utf8_char_start(seg, static_cast<std::size_t>(pos)));
    }
}


// ===========================================================================
// Private: is_blank
// ===========================================================================

bool RollingWindowEngine::is_blank(std::string_view sv) noexcept {
    for (char c : sv) {
        if (!std::isspace(static_cast<unsigned char>(c))) return false;
    }
    return true;
}

} // namespace psycho
