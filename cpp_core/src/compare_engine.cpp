/**
 * compare_engine.cpp
 * ------------------
 * Parallel dual-text BPV analysis.
 *
 * Both texts are dispatched to run_pipeline() via std::async so the two
 * scoring passes run concurrently.  The GIL must be released by the caller
 * (bindings.cpp) before invoking CompareEngine::compare().
 */

#include "compare_engine.h"
#include "pipeline.h"

#include <algorithm>
#include <cmath>
#include <future>
#include <stdexcept>

namespace psycho {

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------

CompareEngine::CompareEngine(int window_size, int stride)
    : window_size_(window_size), stride_(stride)
{
    if (stride_ >= window_size_) {
        throw std::invalid_argument(
            "psycho::CompareEngine — stride must be strictly less than window_size");
    }
}

// ---------------------------------------------------------------------------
// Public: compare
// ---------------------------------------------------------------------------

CompareResult CompareEngine::compare(
    const std::string& text_a,
    const std::string& text_b
) const {
    // Launch both pipeline runs asynchronously on separate threads.
    auto fut_a = std::async(std::launch::async, [&]() {
        return run_pipeline(text_a, window_size_, stride_);
    });
    auto fut_b = std::async(std::launch::async, [&]() {
        return run_pipeline(text_b, window_size_, stride_);
    });

    CompareResult result;
    result.windows_a = fut_a.get();
    result.windows_b = fut_b.get();
    result.alignments = build_alignments(
        result.windows_a,
        result.windows_b,
        text_a.size(),
        text_b.size()
    );
    return result;
}

// ---------------------------------------------------------------------------
// Private: build_alignments
// ---------------------------------------------------------------------------

std::vector<WindowAlignment> CompareEngine::build_alignments(
    const std::vector<WindowResult>& wa,
    const std::vector<WindowResult>& wb,
    std::size_t text_len_a,
    std::size_t text_len_b
) {
    const std::size_t pairs = std::min(wa.size(), wb.size());
    std::vector<WindowAlignment> out;
    out.reserve(pairs);

    for (std::size_t i = 0; i < pairs; ++i) {
        // Normalised midpoint of each window in [0, 1].
        const float mid_a = text_len_a > 0
            ? (static_cast<float>(wa[i].start_char + wa[i].end_char) * 0.5f)
              / static_cast<float>(text_len_a)
            : 0.f;
        const float mid_b = text_len_b > 0
            ? (static_cast<float>(wb[i].start_char + wb[i].end_char) * 0.5f)
              / static_cast<float>(text_len_b)
            : 0.f;

        // Score: 1 − |Δmid|, clamped to [0, 1].
        const float score = std::max(0.f, 1.f - std::abs(mid_a - mid_b));

        out.push_back({
            .index_a        = static_cast<int>(i),
            .index_b        = static_cast<int>(i),
            .position_score = score
        });
    }

    return out;
}

} // namespace psycho
