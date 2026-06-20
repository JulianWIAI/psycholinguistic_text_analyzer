#pragma once
/**
 * cyrillic_engine.h
 * -----------------
 * UTF-8-aware BPV scoring engine for Russian (Cyrillic) text.
 *
 * Structural parity with OrthographicEngine (five-rule pipeline) but operates
 * on Unicode codepoint indices rather than raw ASCII bytes:
 *
 *   1. UTF-8 decode stream → int[] of Cyrillic indices 0–32
 *   2. Pass A: double-letter Gm (Rule 4)
 *   3. Pass B: interaction coefficient pairs (Rule 5)
 *   4. Pass C: standard positional scoring (Rules 1–3)
 *   5. Visual complexity multiplier (×1.2)
 *   6. Normalize to MicroVector six-axis output
 *
 * The Latin OrthographicEngine is untouched. This class is a sibling,
 * not a replacement; the pipeline routes to the correct engine via lang param.
 *
 * Thread-safety: CyrillicOrthographicEngine is stateless — safe to share
 * across threads without synchronization.
 */

#include "types.h"
#include "bpv_table.h"     // POS_START / POS_MIDDLE / POS_END (shared constants)
#include "ru_bpv_table.h"
#include <string_view>

namespace psycho {

// ---------------------------------------------------------------------------
// Cyrillic-specific scoring accumulator (33 bins)
// ---------------------------------------------------------------------------
struct CyrillicMicroScore {
    double raw_score                          = 0.0;
    int    total_chars                        = 0;
    int    total_words                        = 0;
    double letter_totals[ru::ALPHA_SIZE]      = {};
    int    char_counts[ru::ALPHA_SIZE]        = {};
    int    double_letter_counts[ru::ALPHA_SIZE] = {};
    int    words_with_visual_complexity       = 0;
};

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------
class CyrillicOrthographicEngine {
public:
    CyrillicOrthographicEngine() = default;

    CyrillicOrthographicEngine(const CyrillicOrthographicEngine&)            = default;
    CyrillicOrthographicEngine& operator=(const CyrillicOrthographicEngine&) = default;

    /// Full pipeline for one UTF-8 text window → normalized MicroVector.
    [[nodiscard]] MicroVector analyze(std::string_view utf8_text) const;

    /// Raw scoring pass — fills all CyrillicMicroScore fields.
    [[nodiscard]] CyrillicMicroScore score_window(std::string_view utf8_text) const;

    /// Convert CyrillicMicroScore → six normalized MicroVector values.
    [[nodiscard]] MicroVector to_vectors(const CyrillicMicroScore& s) const noexcept;

    /// Populate WindowResult::top_micro_chars and double_letter_anomalies
    /// from a CyrillicMicroScore using Cyrillic glyph strings.
    void fill_telemetry(const CyrillicMicroScore& ms, WindowResult& wr) const;

private:
    static constexpr int MAX_WORD = 128;

    /// Score one word (already decoded into a Cyrillic index array).
    void score_word(
        const int*          indices,
        int                 n,
        CyrillicMicroScore& out
    ) const noexcept;

    void pass_double_letters(
        const int* indices,
        int        n,
        double*    contributions,
        bool*      consumed,
        int*       dl_counts
    ) const noexcept;

    void pass_interactions(
        const int* indices,
        int        n,
        double*    contributions,
        bool*      consumed
    ) const noexcept;
};

} // namespace psycho
