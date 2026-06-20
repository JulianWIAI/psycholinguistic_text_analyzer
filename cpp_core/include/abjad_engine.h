#pragma once
/**
 * abjad_engine.h
 * --------------
 * UTF-8-aware BPV scoring engine for Arabic (AR, 28-bin) and Farsi (FA, 32-bin).
 *
 * Structural parity with CyrillicOrthographicEngine (five-rule pipeline):
 *   1. UTF-8 decode stream → int[] of Abjad indices (0–27 AR / 0–31 FA)
 *   2. Pass A: double-letter Gm (Rule 4)
 *   3. Pass B: interaction coefficient pairs (Rule 5)
 *   4. Pass C: standard positional scoring (Rules 1–3)
 *   5. Visual complexity multiplier (×1.2 for emphatic/pharyngeal words)
 *   6. Normalize to MicroVector six-axis output
 *
 * Six-axis psychological mapping (mirrors Cyrillic axis semantics):
 *   anxiety   → ن(24) + س(11)  nasal + sibilant tension   [mirrors RU: Н+С]
 *   attention → ا(0)  + ع(17)  vowel-base + pharyngeal     [mirrors RU: А+К]
 *   emotion   → م(23) + و(26)  nasal + semivowel           [mirrors RU: М+Ю]
 *   agitation → ر(9)  + ج(4)  trill + affricate            [mirrors RU: Р+З]
 *
 * CRITICAL — Logical vs. Visual Order:
 *   AbjadOrthographicEngine processes the UTF-8 byte stream in logical order
 *   (the exact sequence keystrokes were typed). No string reversal is applied.
 *   RTL rendering is strictly a UI-layer concern.
 *
 * Thread-safety: AbjadOrthographicEngine is stateless — safe to share.
 */

#include "types.h"
#include "bpv_table.h"      // POS_START / POS_MIDDLE / POS_END (shared)
#include "ar_bpv_table.h"
#include "ru_bpv_table.h"   // provides the shared utf8_next() decoder
#include <string_view>

namespace psycho {

// ---------------------------------------------------------------------------
// Abjad scoring accumulator — 32 bins cover both AR (28) and FA (32)
// The alpha_size field tells callers how many bins are active.
// ---------------------------------------------------------------------------
struct AbjadMicroScore {
    int    alpha_size                           = 0;  // 28 for AR, 32 for FA
    double raw_score                            = 0.0;
    int    total_chars                          = 0;
    int    total_words                          = 0;
    double letter_totals[ar::ALPHA_SIZE_FA]     = {};
    int    char_counts[ar::ALPHA_SIZE_FA]       = {};
    int    double_letter_counts[ar::ALPHA_SIZE_FA] = {};
    int    words_with_visual_complexity         = 0;
};

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------
class AbjadOrthographicEngine {
public:
    /// @param is_farsi  True → FA 32-bin mode; false → AR 28-bin mode.
    explicit AbjadOrthographicEngine(bool is_farsi = false) noexcept
        : is_farsi_(is_farsi)
        , alpha_size_(is_farsi ? ar::ALPHA_SIZE_FA : ar::ALPHA_SIZE_AR)
    {}

    AbjadOrthographicEngine(const AbjadOrthographicEngine&)            = default;
    AbjadOrthographicEngine& operator=(const AbjadOrthographicEngine&) = default;

    /// Full pipeline: one UTF-8 text window → normalized MicroVector.
    [[nodiscard]] MicroVector analyze(std::string_view utf8_text) const;

    /// Raw scoring pass — fills all AbjadMicroScore fields.
    [[nodiscard]] AbjadMicroScore score_window(std::string_view utf8_text) const;

    /// Convert AbjadMicroScore → six normalized MicroVector values.
    [[nodiscard]] MicroVector to_vectors(const AbjadMicroScore& s) const noexcept;

    /// Populate WindowResult::top_micro_chars and double_letter_anomalies
    /// from an AbjadMicroScore using the correct glyph table (AR or FA).
    void fill_telemetry(const AbjadMicroScore& ms, WindowResult& wr) const;

    bool is_farsi()    const noexcept { return is_farsi_; }
    int  alpha_size()  const noexcept { return alpha_size_; }

private:
    bool is_farsi_;
    int  alpha_size_;

    static constexpr int MAX_WORD = 128;

    inline uint8_t bpv(int idx) const noexcept {
        return is_farsi_ ? ar::bpv_fa(idx) : ar::bpv_ar(idx);
    }
    inline double double_gm(int idx) const noexcept {
        return ar::double_gm_ar(idx, is_farsi_);
    }
    inline bool is_visual_anchor(int idx) const noexcept {
        return ar::is_visual_anchor_ar(idx);
    }
    inline const char* glyph(int idx) const noexcept {
        if (idx < 0 || idx >= alpha_size_) return "?";
        return is_farsi_ ? ar::FA_GLYPH[idx] : ar::AR_GLYPH[idx];
    }

    void score_word(
        const int*      indices,
        int             n,
        AbjadMicroScore& out
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
