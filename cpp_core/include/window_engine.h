#pragma once
/**
 * window_engine.h
 * ---------------
 * Zero-copy rolling window tokenizer.
 *
 * Design contract:
 *   - All TextWindow::text fields are std::string_view slices into the
 *     original document buffer.  No heap allocation for window text.
 *   - Hard Reset Rule: when a structural boundary (double newline or a
 *     chapter/section heading) is found, the current segment is emitted
 *     immediately and the sliding window restarts from the next character.
 *     This prevents psychological signal from bleeding across boundaries.
 *   - Thread-safe: all methods are const / stateless after construction.
 */

#include "types.h"
#include <string_view>
#include <vector>
#include <string>
#include <cstddef>
#include <stdexcept>

namespace psycho {

class RollingWindowEngine {
public:
    /**
     * @param window_size  Number of characters per analysis window (default 1000).
     * @param stride       Step between successive windows (default 500).
     *                     Must be strictly less than window_size.
     */
    explicit RollingWindowEngine(int window_size = 1000, int stride = 500);

    /**
     * Tokenize *text* into overlapping TextWindow views.
     *
     * @param text  The full document.  Must remain alive for as long as the
     *              returned TextWindow::text views are accessed.
     * @return      Vector of windows in document order.
     */
    [[nodiscard]]
    std::vector<TextWindow> tokenize(std::string_view text) const;

private:
    // ── Boundary detection ────────────────────────────────────────────────

    struct Boundary {
        std::size_t b_start;  // first char of the boundary marker
        std::size_t b_end;    // first char AFTER the boundary marker
        std::string type;     // "double_newline" | "heading"
    };

    /// Find all structural boundaries in *text* and return them unsorted.
    std::vector<Boundary> find_boundaries(std::string_view text) const;

    /// Returns true if the character at *pos* starts a heading keyword or
    /// a "1." / "2." style section marker, assuming it is at line start.
    bool is_heading_start(std::string_view text, std::size_t pos) const noexcept;

    // ── Sliding window ────────────────────────────────────────────────────

    /**
     * Emit overlapping windows from a single flat segment and append them
     * to *out*.
     *
     * @param seg                 View of the segment (slice of original text).
     * @param offset              Absolute byte offset of seg within original text.
     * @param global_idx          Next window index to assign; incremented in place.
     * @param is_boundary_segment True → first window gets reset_reason="structural_boundary".
     * @param out                 Output accumulator.
     */
    void slide_segment(
        std::string_view        seg,
        std::size_t             offset,
        int&                    global_idx,
        bool                    is_boundary_segment,
        std::vector<TextWindow>& out
    ) const;

    // ── Utilities ─────────────────────────────────────────────────────────

    /// True if every character in *sv* is ASCII whitespace.
    static bool is_blank(std::string_view sv) noexcept;

    // ── Configuration ─────────────────────────────────────────────────────
    int window_size_;
    int stride_;
};

} // namespace psycho
