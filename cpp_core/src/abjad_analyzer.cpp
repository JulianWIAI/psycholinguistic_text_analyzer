/**
 * abjad_analyzer.cpp
 * ------------------
 * UTF-8-aware five-rule BPV scoring pipeline for Arabic (28-bin) and Farsi (32-bin).
 *
 * Words are accumulated as int[MAX_WORD] arrays of resolved Abjad indices
 * decoded from UTF-8 multibyte sequences.  Any codepoint that is NOT a
 * recognized Arabic/Farsi consonant (punctuation, whitespace, diacritics,
 * harakat, Latin characters, digits) signals a word boundary.
 *
 * Arabic diacritics (harakat, U+064B–U+065F) are silently skipped — they
 * carry no phonemic weight in the BPV model, only voweling annotation.
 * Arabic tatweel (U+0640) is also skipped.
 *
 * Structural parity with cyrillic_analyzer.cpp:
 *   Pass A (double-letter Gm) → Pass B (interactions) → Pass C (positional BPV).
 *   Consumed slots carry their special-rule contribution; un-consumed fall through.
 *
 * CRITICAL — Logical vs. Visual Order:
 *   This engine processes the byte stream exactly as received (logical order).
 *   No reversal is applied.  For RTL Abjad text, this means the first indexed
 *   character is the rightmost visible glyph, which is the correct forensic
 *   representation of keystroke sequence.
 */

#include "abjad_engine.h"
#include <algorithm>
#include <string>

namespace psycho {

// ===========================================================================
// Public interface
// ===========================================================================

MicroVector AbjadOrthographicEngine::analyze(std::string_view utf8_text) const {
    return to_vectors(score_window(utf8_text));
}

AbjadMicroScore AbjadOrthographicEngine::score_window(
    std::string_view utf8_text
) const {
    AbjadMicroScore out{};
    out.alpha_size = alpha_size_;

    int         word_buf[MAX_WORD];
    int         word_len = 0;

    const auto*       s = reinterpret_cast<const unsigned char*>(utf8_text.data());
    const std::size_t n = utf8_text.size();

    auto flush_word = [&]() noexcept {
        if (word_len == 0) return;
        const int used = std::min(word_len, MAX_WORD);
        out.total_chars += used;
        ++out.total_words;
        score_word(word_buf, used, out);
        word_len = 0;
    };

    std::size_t i = 0;
    while (i < n) {
        // Use the shared utf8_next() decoder from the Cyrillic engine.
        // It handles all 2-byte and 3-byte sequences, including the entire
        // U+0600–U+06FF Arabic/Farsi block.
        const uint32_t cp  = ru::utf8_next(s, n, i);

        // Arabic diacritics / harakat (U+064B–U+065F) and tatweel (U+0640)
        // are not letters — skip without flushing the current word.
        if (cp >= 0x064Bu && cp <= 0x065Fu) continue;
        if (cp == 0x0640u) continue;

        const int idx = ar::arabic_index(cp, is_farsi_);

        if (idx >= 0) {
            if (word_len < MAX_WORD)
                word_buf[word_len] = idx;
            ++word_len;
        } else {
            flush_word();
        }
    }
    flush_word();

    if (out.total_chars == 0) out.total_chars = 1;
    return out;
}

MicroVector AbjadOrthographicEngine::to_vectors(
    const AbjadMicroScore& s
) const noexcept {
    double total_bpv = 0.0;
    for (int i = 0; i < alpha_size_; ++i) total_bpv += s.letter_totals[i];
    if (total_bpv < 1.0) total_bpv = 1.0;

    // Six-axis psychological mapping for Arabic/Farsi:
    //   anxiety   → ن(24) + س(11)  nasal + sibilant tension
    //   attention → ا(0)  + ع(17)  vowel base + pharyngeal
    //   emotion   → م(23) + و(26)  nasal + semivowel
    //   agitation → ر(9)  + ج(4)   trill + affricate
    return MicroVector{
        .intensity  = s.raw_score / static_cast<double>(s.total_chars),
        .anxiety    = (s.letter_totals[24] + s.letter_totals[11]) / total_bpv * 100.0,
        .attention  = (s.letter_totals[ 0] + s.letter_totals[17]) / total_bpv * 100.0,
        .emotion    = (s.letter_totals[23] + s.letter_totals[26]) / total_bpv * 100.0,
        .agitation  = (s.letter_totals[ 9] + s.letter_totals[ 4]) / total_bpv * 100.0,
        .complexity = static_cast<double>(s.words_with_visual_complexity),
    };
}

void AbjadOrthographicEngine::fill_telemetry(
    const AbjadMicroScore& ms,
    WindowResult&          wr
) const {
    struct Entry { int idx; int count; };
    Entry entries[ar::ALPHA_SIZE_FA];
    for (int i = 0; i < alpha_size_; ++i)
        entries[i] = { i, ms.char_counts[i] };

    const int top_n = std::min(5, alpha_size_);
    std::partial_sort(
        entries,
        entries + top_n,
        entries + alpha_size_,
        [](const Entry& a, const Entry& b) { return a.count > b.count; }
    );

    for (int i = 0; i < top_n; ++i) {
        if (entries[i].count == 0) break;
        wr.top_micro_chars[glyph(entries[i].idx)] = entries[i].count;
    }

    for (int i = 0; i < alpha_size_; ++i) {
        if (ms.double_letter_counts[i] > 0) {
            const char* g = glyph(i);
            std::string pair = std::string(g) + g;
            wr.double_letter_anomalies[pair] = ms.double_letter_counts[i];
        }
    }
}


// ===========================================================================
// Private: score_word
// ===========================================================================

void AbjadOrthographicEngine::score_word(
    const int*      indices,
    int             n,
    AbjadMicroScore& out
) const noexcept {
    double contributions[MAX_WORD] = {};
    bool   consumed[MAX_WORD]      = {};

    pass_double_letters(indices, n, contributions, consumed, out.double_letter_counts);
    pass_interactions(indices, n, contributions, consumed);

    double word_score = 0.0;
    for (int i = 0; i < n; ++i) word_score += contributions[i];

    bool has_visual = false;

    for (int i = 0; i < n; ++i) {
        const int idx = indices[i];
        if (idx < 0 || idx >= alpha_size_) continue;

        if (is_visual_anchor(idx)) has_visual = true;

        out.letter_totals[idx] += static_cast<double>(bpv(idx));
        out.char_counts[idx]++;

        if (!consumed[i]) {
            const uint8_t b = bpv(idx);
            if (b == 0) continue;
            const double pos_mult =
                (i == 0)     ? POS_START  :
                (i == n - 1) ? POS_END    :
                               POS_MIDDLE;
            word_score += static_cast<double>(b) * pos_mult;
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

void AbjadOrthographicEngine::pass_double_letters(
    const int* indices,
    int        n,
    double*    contributions,
    bool*      consumed,
    int*       dl_counts
) const noexcept {
    int i = 0;
    while (i < n - 1) {
        const int idx = indices[i];
        if (idx >= 0 && idx == indices[i + 1]) {
            const double gm   = double_gm(idx);
            const double half = static_cast<double>(bpv(idx)) * gm / 2.0;

            contributions[i]     = half;
            contributions[i + 1] = half;
            consumed[i]          = true;
            consumed[i + 1]      = true;
            dl_counts[idx]++;
            i += 2;
        } else {
            ++i;
        }
    }
}


// ===========================================================================
// Private: pass_interactions  (Rule 5)
// ===========================================================================

void AbjadOrthographicEngine::pass_interactions(
    const int* indices,
    int        n,
    double*    contributions,
    bool*      consumed
) const noexcept {
    for (int a = 0; a < n; ++a) {
        const int b_limit = std::min(a + 3, n);
        for (int b = a + 1; b < b_limit; ++b) {
            const int ia = indices[a];
            const int ib = indices[b];
            if (ia < 0 || ib < 0) continue;

            // Interaction table is the same for both AR and FA — the 7 pairs
            // are all within the shared 28-letter Arabic core.
            const ar::AbjadInteractionCoeff* coeff =
                ar::find_interaction_ar(ia, ib);
            if (!coeff) continue;

            const double p_d = (b - a == 1) ? 1.0 : 0.5;
            const double pair_score =
                (static_cast<double>(bpv(ia)) +
                 static_cast<double>(bpv(ib)))
                * coeff->ic * p_d;

            if (!consumed[a]) { contributions[a] += pair_score / 2.0; consumed[a] = true; }
            if (!consumed[b]) { contributions[b] += pair_score / 2.0; consumed[b] = true; }
        }
    }
}

} // namespace psycho
