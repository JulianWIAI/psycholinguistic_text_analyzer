#pragma once
/**
 * compare_engine.h
 * ----------------
 * Parallel dual-text micro-layer analysis engine.
 *
 * Accepts two documents and processes them concurrently on separate
 * std::async threads, both fed through the shared run_pipeline()
 * (RollingWindowEngine → OrthographicEngine). The caller (bindings.cpp)
 * receives independent window sequences that the Python layer then merges
 * with macro (spaCy) scores and dissonance events.
 *
 * The engine also produces a per-window alignment vector: for each shared
 * index i, the alignment_score reflects how close the normalised
 * character-position midpoints are (1.0 = perfect overlap, 0.0 = opposite
 * ends of the respective documents). This lets the UI highlight windows
 * that are "positionally equivalent" across the two texts.
 *
 * Thread-safety: CompareEngine is stateless after construction.
 */

#include "types.h"
#include <string>
#include <vector>
#include <cstddef>

namespace psycho {

// ---------------------------------------------------------------------------
// Alignment between one window from text A and one from text B at the same
// sequential index.
// ---------------------------------------------------------------------------
struct WindowAlignment {
    int   index_a        = 0;   ///< Index in text A's window sequence
    int   index_b        = 0;   ///< Index in text B's window sequence
    float position_score = 0.f; ///< 1.0 = same relative position; 0.0 = opposite ends
};

// ---------------------------------------------------------------------------
// Complete result of one parallel dual-text comparison pass.
// ---------------------------------------------------------------------------
struct CompareResult {
    std::vector<WindowResult>    windows_a;  ///< All windows from text A (BPV scored)
    std::vector<WindowResult>    windows_b;  ///< All windows from text B (BPV scored)
    std::vector<WindowAlignment> alignments; ///< One entry per min(|A|, |B|) index
};

// ---------------------------------------------------------------------------
// CompareEngine
// ---------------------------------------------------------------------------
class CompareEngine {
public:
    /**
     * @param window_size  Characters per analysis window (default 1000).
     * @param stride       Slide step; must be strictly less than window_size.
     */
    explicit CompareEngine(int window_size = 1000, int stride = 500);

    /**
     * Process text_a and text_b in parallel on separate async threads.
     *
     * The GIL is NOT touched here — this is pure C++ and must only be called
     * from within a py::gil_scoped_release block in bindings.cpp.
     *
     * @param text_a  First document.
     * @param text_b  Second document.
     * @return        CompareResult with windows_a, windows_b, and alignments.
     */
    [[nodiscard]]
    CompareResult compare(const std::string& text_a,
                          const std::string& text_b) const;

private:
    int window_size_;
    int stride_;

    /// Compute positional alignment for each shared-index window pair.
    static std::vector<WindowAlignment> build_alignments(
        const std::vector<WindowResult>& wa,
        const std::vector<WindowResult>& wb,
        std::size_t text_len_a,
        std::size_t text_len_b
    );
};

} // namespace psycho
