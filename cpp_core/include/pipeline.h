#pragma once
/**
 * pipeline.h
 * ----------
 * Single-document BPV scoring pipeline:
 *   text → RollingWindowEngine → OrthographicEngine → vector<WindowResult>
 *
 * Extracted from bindings.cpp so that both the single-analyze and
 * compare-analyze bindings can share the same implementation without
 * duplicating code.
 *
 * Thread-safety: run_pipeline() is stateless and safe to call from
 * multiple threads concurrently.
 */

#include "types.h"
#include <string>
#include <vector>

namespace psycho {

/**
 * Run the full micro-layer BPV pipeline on one document.
 *
 * Tokenises *text* with RollingWindowEngine(window_size, stride), scores
 * each non-blank window with OrthographicEngine, and packages both the
 * normalised MicroVector and the raw telemetry fields into WindowResult.
 *
 * @param text         Source document. Owned by caller; must remain valid
 *                     for the duration of this call.
 * @param window_size  Characters per analysis window (must be > stride).
 * @param stride       Slide step between successive windows.
 * @return             One WindowResult per non-blank window, in document order.
 */
std::vector<WindowResult> run_pipeline(
    const std::string& text,
    int                window_size,
    int                stride
);

} // namespace psycho
