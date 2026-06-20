/**
 * ko_analyzer.cpp
 * ---------------
 * UTF-8-aware five-rule BPV scoring pipeline for Korean (Hangul) Jamo text.
 *
 * Input: Jamo-decomposed UTF-8 string produced by Python's unpack_hangul_to_jamo().
 * Each syllable block has been expanded into conjoining Onset/Nucleus/Coda Jamo
 * (U+1100–U+11FF). Non-Jamo codepoints (spaces, punctuation) act as word boundaries.
 *
 * The word buffer stores {bin, bpv} pairs so tense consonants (BPV=9) score
 * correctly even when folded to a shared base bin.
 *
 * Structural parity with cyrillic_analyzer.cpp:
 *   Pass A (double-letter Gm) → Pass B (interactions) → Pass C (positional BPV)
 *   → visual complexity × 1.2 → MicroVector normalization.
 */

#include "ko_engine.h"
#include <algorithm>
#include <string>

namespace psycho {

// ===========================================================================
// Public interface
// ===========================================================================

MicroVector KoreanOrthographicEngine::analyze(std::string_view utf8_text) const {
    return to_vectors(score_window(utf8_text));
}

KoreanMicroScore KoreanOrthographicEngine::score_window(
    std::string_view utf8_text
) const {
    KoreanMicroScore out{};

    int     bin_buf[MAX_WORD];
    uint8_t bpv_buf[MAX_WORD];
    int     word_len = 0;

    const auto*       s = reinterpret_cast<const unsigned char*>(utf8_text.data());
    const std::size_t n = utf8_text.size();

    auto flush_word = [&]() noexcept {
        if (word_len == 0) return;
        const int used = std::min(word_len, MAX_WORD);
        out.total_chars += used;
        ++out.total_words;
        score_word(bin_buf, bpv_buf, used, out);
        word_len = 0;
    };

    std::size_t i = 0;
    while (i < n) {
        const uint32_t    cp = ru::utf8_next(s, n, i);
        const ko::JamoBin jb = ko::jamo_lookup(cp);

        if (jb.bin >= 0) {
            if (word_len < MAX_WORD) {
                bin_buf[word_len] = jb.bin;
                bpv_buf[word_len] = jb.bpv;
            }
            ++word_len;
        } else {
            flush_word();
        }
    }
    flush_word();

    if (out.total_chars == 0) out.total_chars = 1;
    return out;
}

MicroVector KoreanOrthographicEngine::to_vectors(
    const KoreanMicroScore& s
) const noexcept {
    double total_bpv = 0.0;
    for (int i = 0; i < ko::ALPHA_SIZE; ++i) total_bpv += s.letter_totals[i];
    if (total_bpv < 1.0) total_bpv = 1.0;

    // Six-axis psychological mapping for Korean Jamo:
    //   anxiety    → ㅅ(6) + ㄴ(1)   sibilant tension + nasal   [mirrors S+N in Latin]
    //   attention  → ㄱ(0) + ㅇ(7)   leading plosive + silent   [mirrors A+K in Latin]
    //   emotion    → ㅁ(4) + ㅏ(14)  somatic nasal + open vowel [mirrors M+W in Latin]
    //   agitation  → ㄹ(3) + ㅈ(8)   liquid + affricate         [mirrors R+Z in Latin]
    return MicroVector{
        .intensity  = s.raw_score / static_cast<double>(s.total_chars),
        .anxiety    = (s.letter_totals[6] + s.letter_totals[1])  / total_bpv * 100.0,
        .attention  = (s.letter_totals[0] + s.letter_totals[7])  / total_bpv * 100.0,
        .emotion    = (s.letter_totals[4] + s.letter_totals[14]) / total_bpv * 100.0,
        .agitation  = (s.letter_totals[3] + s.letter_totals[8])  / total_bpv * 100.0,
        .complexity = static_cast<double>(s.words_with_visual_complexity),
    };
}

void KoreanOrthographicEngine::fill_telemetry(
    const KoreanMicroScore& ms,
    WindowResult&           wr
) const {
    struct Entry { int idx; int count; };
    Entry entries[ko::ALPHA_SIZE];
    for (int i = 0; i < ko::ALPHA_SIZE; ++i)
        entries[i] = { i, ms.char_counts[i] };

    std::partial_sort(
        entries,
        entries + std::min(5, ko::ALPHA_SIZE),
        entries + ko::ALPHA_SIZE,
        [](const Entry& a, const Entry& b) { return a.count > b.count; }
    );

    for (int i = 0; i < 5; ++i) {
        if (entries[i].count == 0) break;
        wr.top_micro_chars[ko::KO_GLYPH[entries[i].idx]] = entries[i].count;
    }

    for (int i = 0; i < ko::ALPHA_SIZE; ++i) {
        if (ms.double_letter_counts[i] > 0) {
            std::string pair =
                std::string(ko::KO_GLYPH[i]) + ko::KO_GLYPH[i];
            wr.double_letter_anomalies[pair] = ms.double_letter_counts[i];
        }
    }
}


// ===========================================================================
// Private: score_word
// ===========================================================================

void KoreanOrthographicEngine::score_word(
    const int*        bins,
    const uint8_t*    bpvs,
    int               n,
    KoreanMicroScore& out
) const noexcept {
    double contributions[MAX_WORD] = {};
    bool   consumed[MAX_WORD]      = {};

    pass_double_letters(bins, bpvs, n, contributions, consumed, out.double_letter_counts);
    pass_interactions(bins, bpvs, n, contributions, consumed);

    double word_score = 0.0;
    for (int i = 0; i < n; ++i) word_score += contributions[i];

    bool has_visual = false;

    for (int i = 0; i < n; ++i) {
        const int     bin = bins[i];
        const uint8_t bpv = bpvs[i];
        if (bin < 0 || bin >= ko::ALPHA_SIZE) continue;

        if (ko::is_visual_anchor_ko(bin)) has_visual = true;

        out.letter_totals[bin] += static_cast<double>(bpv);
        out.char_counts[bin]++;

        if (!consumed[i]) {
            if (bpv == 0) continue;
            const double pos_mult =
                (i == 0)     ? POS_START  :
                (i == n - 1) ? POS_END    :
                               POS_MIDDLE;
            word_score += static_cast<double>(bpv) * pos_mult;
        }
    }

    if (has_visual) {
        word_score *= 1.2;
        ++out.words_with_visual_complexity;
    }

    out.raw_score += word_score;
}


// ===========================================================================
// Private: pass_double_letters  (Rule 4)
// ===========================================================================

void KoreanOrthographicEngine::pass_double_letters(
    const int*     bins,
    const uint8_t* bpvs,
    int            n,
    double*        contributions,
    bool*          consumed,
    int*           dl_counts
) const noexcept {
    int i = 0;
    while (i < n - 1) {
        const int bin = bins[i];
        if (bin >= 0 && bin == bins[i + 1]) {
            const double gm   = ko::double_gm_ko(bin);
            const double half = static_cast<double>(bpvs[i]) * gm / 2.0;

            contributions[i]     = half;
            contributions[i + 1] = half;
            consumed[i]          = true;
            consumed[i + 1]      = true;
            dl_counts[bin]++;
            i += 2;
        } else {
            ++i;
        }
    }
}


// ===========================================================================
// Private: pass_interactions  (Rule 5)
// ===========================================================================

void KoreanOrthographicEngine::pass_interactions(
    const int*     bins,
    const uint8_t* bpvs,
    int            n,
    double*        contributions,
    bool*          consumed
) const noexcept {
    for (int a = 0; a < n; ++a) {
        const int b_limit = std::min(a + 3, n);
        for (int b = a + 1; b < b_limit; ++b) {
            const int ba = bins[a];
            const int bb = bins[b];
            if (ba < 0 || bb < 0) continue;

            const ko::KoreanInteractionCoeff* coeff =
                ko::find_interaction_ko(ba, bb);
            if (!coeff) continue;

            const double p_d = (b - a == 1) ? 1.0 : 0.5;
            const double pair_score =
                (static_cast<double>(bpvs[a]) + static_cast<double>(bpvs[b]))
                * coeff->ic * p_d;

            if (!consumed[a]) { contributions[a] += pair_score / 2.0; consumed[a] = true; }
            if (!consumed[b]) { contributions[b] += pair_score / 2.0; consumed[b] = true; }
        }
    }
}

} // namespace psycho
