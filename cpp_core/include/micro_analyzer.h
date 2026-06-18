#pragma once
/**
 * micro_analyzer.h
 * ----------------
 * Orthographic BPV scoring engine — the C++ translation of
 * micro_layer/orthographic_analyzer.py.
 *
 * Five-rule pipeline (applied identically to the Python version):
 *   1. Base Psychological Vectors  — per-letter integer weight (A=8 … Z=9)
 *   2. Positional Modifier (μ_p)   — start×1.5  middle×1.0  end×0.75
 *   3. Visual Complexity Anchor    — word contains W/M/K → word_score×1.2
 *   4. Phonosemantic Gm            — exact double-letter → Gm multiplier
 *   5. Interaction Coefficients    — adjacent pair within 2 positions → I_c
 *
 * Rules 4 and 5 claim their positions first (consumed flag).
 * Rule 2 applies only to positions not already consumed.
 *
 * v2 additions (Raw Telemetry):
 *   score_window() now also fills MicroScore::total_words,
 *   char_counts[26], and double_letter_counts[26] so bindings.cpp can
 *   surface raw frequency telemetry without a second pass over the text.
 *
 * Thread-safety: OrthographicEngine holds zero mutable state.
 * The same instance can be shared across threads without synchronization.
 */

#include "types.h"
#include "bpv_table.h"
#include <string_view>

namespace psycho {

class OrthographicEngine {
public:
    OrthographicEngine() = default;

    OrthographicEngine(const OrthographicEngine&)            = default;
    OrthographicEngine& operator=(const OrthographicEngine&) = default;

    /**
     * Full pipeline for one text window.
     * Equivalent to Python's OrthographicAnalyzer.analyze().
     * @return Normalized six-vector MicroVector.
     */
    [[nodiscard]] MicroVector analyze(std::string_view text) const;

    /**
     * Raw scoring pass — fills ALL MicroScore fields including the new
     * telemetry arrays (char_counts, double_letter_counts, total_words).
     * Use this when the caller needs to inspect raw data before normalization.
     */
    [[nodiscard]] MicroScore score_window(std::string_view text) const;

    /**
     * Convert a raw MicroScore to the six normalized MicroVector values.
     * Equivalent to Python's _to_result().
     */
    [[nodiscard]] MicroVector to_vectors(const MicroScore& s) const noexcept;

private:
    // ── Per-word scoring ──────────────────────────────────────────────────

    /// Score one UPPER-CASED word and accumulate into *out*.
    void score_word(const char* word, int n, MicroScore& out) const noexcept;

    /**
     * Rule 4: scan for adjacent identical letters (e.g. "ss", "ll").
     * Marks consumed[i] and consumed[i+1] true; sets contributions[i/i+1].
     * Skips i+=2 when a pair is found so no pair is counted twice.
     *
     * @param dl_counts  Pointer to MicroScore::double_letter_counts[26].
     *                   Incremented at index (letter - 'A') for every pair found.
     */
    void pass_double_letters(
        const char* word,
        int         n,
        double*     contributions,
        bool*       consumed,
        int*        dl_counts
    ) const noexcept;

    /**
     * Rule 5: interaction coefficient pairs within a look-ahead window of 2.
     * Only the FIRST interaction that claims a position is recorded
     * (mirrors Python's `if idx not in consumed` check).
     */
    void pass_interactions(
        const char* word,
        int         n,
        double*     contributions,
        bool*       consumed
    ) const noexcept;

    static constexpr int MAX_WORD = 128;
};

} // namespace psycho
