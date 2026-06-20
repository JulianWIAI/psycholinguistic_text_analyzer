#pragma once
/**
 * ko_engine.h
 * -----------
 * UTF-8-aware BPV scoring engine for Korean (Hangul) Jamo text.
 *
 * The engine operates on Jamo-decomposed text produced by the Python bridge
 * (unpack_hangul_to_jamo). Each Hangul syllable block (U+AC00–U+D7A3) must
 * be pre-decomposed into conjoining Jamo (U+1100–U+11FF) by Python before
 * the byte stream reaches this layer.
 *
 * Structural parity with CyrillicOrthographicEngine (five-rule pipeline):
 *   1. UTF-8 decode stream → per-jamo {bin, bpv} pairs
 *   2. Pass A: double-letter Gm (Rule 4)
 *   3. Pass B: interaction coefficient pairs (Rule 5)
 *   4. Pass C: standard positional scoring (Rules 1–3)
 *   5. Visual complexity multiplier (×1.2)
 *   6. Normalize to MicroVector six-axis output
 *
 * Word buffer stores both bin index and per-jamo BPV so tense consonants
 * (ㄲ ㄸ ㅃ ㅆ ㅉ) correctly contribute BPV=9 even though they fold to a
 * shared base bin.
 *
 * Thread-safety: KoreanOrthographicEngine is stateless.
 */

#include "types.h"
#include "bpv_table.h"      // POS_START / POS_MIDDLE / POS_END
#include "ko_bpv_table.h"
#include "ru_bpv_table.h"   // ru::utf8_next — shared 3/4-byte UTF-8 decoder
#include <string_view>

namespace psycho {

// ---------------------------------------------------------------------------
// Korean scoring accumulator (24 bins)
// ---------------------------------------------------------------------------
struct KoreanMicroScore {
    double raw_score                            = 0.0;
    int    total_chars                          = 0;  // jamo count (Python overrides with syllable count)
    int    total_words                          = 0;
    double letter_totals[ko::ALPHA_SIZE]        = {};
    int    char_counts[ko::ALPHA_SIZE]          = {};
    int    double_letter_counts[ko::ALPHA_SIZE] = {};
    int    words_with_visual_complexity         = 0;
};

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------
class KoreanOrthographicEngine {
public:
    KoreanOrthographicEngine() = default;
    KoreanOrthographicEngine(const KoreanOrthographicEngine&)            = default;
    KoreanOrthographicEngine& operator=(const KoreanOrthographicEngine&) = default;

    [[nodiscard]] MicroVector analyze(std::string_view utf8_text) const;
    [[nodiscard]] KoreanMicroScore score_window(std::string_view utf8_text) const;
    [[nodiscard]] MicroVector to_vectors(const KoreanMicroScore& s) const noexcept;
    void fill_telemetry(const KoreanMicroScore& ms, WindowResult& wr) const;

private:
    // Korean words can be long when decomposed (avg ~3 syllables × ~2.5 jamo = ~7.5 jamo per word)
    static constexpr int MAX_WORD = 256;

    void score_word(
        const int*     bins,
        const uint8_t* bpvs,
        int            n,
        KoreanMicroScore& out
    ) const noexcept;

    void pass_double_letters(
        const int*     bins,
        const uint8_t* bpvs,
        int            n,
        double*        contributions,
        bool*          consumed,
        int*           dl_counts
    ) const noexcept;

    void pass_interactions(
        const int*     bins,
        const uint8_t* bpvs,
        int            n,
        double*        contributions,
        bool*          consumed
    ) const noexcept;
};

} // namespace psycho
