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

/**
 * Cyrillic (Russian) variant — UTF-8 codepoint iterator + 33-bin BPV.
 * Routes to CyrillicOrthographicEngine; Latin path is completely unaffected.
 */
std::vector<WindowResult> run_pipeline_ru(
    const std::string& text,
    int                window_size,
    int                stride
);

/**
 * Arabic variant — UTF-8 codepoint iterator + 28-bin Abjad BPV.
 * Routes to AbjadOrthographicEngine(is_farsi=false).
 * The byte stream is processed in logical order (keystroke sequence);
 * no RTL reversal is performed in this layer.
 */
std::vector<WindowResult> run_pipeline_ar(
    const std::string& text,
    int                window_size,
    int                stride
);

/**
 * Farsi variant — UTF-8 codepoint iterator + 32-bin Abjad BPV.
 * Routes to AbjadOrthographicEngine(is_farsi=true).
 * Extends the 28-bin Arabic core with پ چ ژ گ at indices 28–31.
 */
std::vector<WindowResult> run_pipeline_fa(
    const std::string& text,
    int                window_size,
    int                stride
);

/**
 * Korean variant — UTF-8 conjoining Jamo iterator + 24-bin Jamo BPV.
 * Routes to KoreanOrthographicEngine.
 * Input must be Jamo-decomposed by Python's unpack_hangul_to_jamo() before
 * reaching this layer (syllable blocks U+AC00–U+D7A3 are not handled here).
 * top_micro_chars keys are Jamo glyph strings (e.g. "ㄱ", "ㅏ").
 */
std::vector<WindowResult> run_pipeline_ko(
    const std::string& text,
    int                window_size,
    int                stride
);

} // namespace psycho
