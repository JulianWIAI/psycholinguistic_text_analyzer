/**
 * cyrillic_analyzer.cpp
 * ---------------------
 * UTF-8-aware five-rule BPV scoring pipeline for Russian (Cyrillic) text.
 *
 * Words are accumulated as int[MAX_WORD] arrays of resolved Cyrillic indices
 * (0–32) decoded from UTF-8 multibyte sequences.  Every word boundary is
 * signalled by any codepoint that is NOT a Cyrillic letter (punctuation,
 * whitespace, Latin characters, digits, control characters).
 *
 * Structural parity with micro_analyzer.cpp:
 *   Pass A (double-letter Gm) runs before Pass B (interactions),
 *   which runs before Pass C (positional BPV).  Consumed slots carry their
 *   contribution from the special rule only; un-consumed slots fall through
 *   to the standard positional scorer.
 */

#include "cyrillic_engine.h"
#include <algorithm>
#include <string>

namespace psycho {

// ===========================================================================
// Public interface
// ===========================================================================

MicroVector CyrillicOrthographicEngine::analyze(std::string_view utf8_text) const {
    return to_vectors(score_window(utf8_text));
}

CyrillicMicroScore CyrillicOrthographicEngine::score_window(
    std::string_view utf8_text
) const {
    CyrillicMicroScore out{};

    int         word_buf[MAX_WORD];
    int         word_len = 0;

    const auto*       s = reinterpret_cast<const unsigned char*>(utf8_text.data());
    const std::size_t n = utf8_text.size();

    // Flush the current word buffer into the scoring engine.
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
        const uint32_t cp  = ru::utf8_next(s, n, i);
        const int      idx = ru::cyrillic_index(cp);

        if (idx >= 0) {
            // Valid Cyrillic letter — append to current word.
            if (word_len < MAX_WORD)
                word_buf[word_len] = idx;
            ++word_len;
        } else {
            // Word boundary (space, punct, Latin, digit, control …)
            flush_word();
        }
    }
    flush_word(); // trailing word with no terminating delimiter

    if (out.total_chars == 0) out.total_chars = 1;
    return out;
}

MicroVector CyrillicOrthographicEngine::to_vectors(
    const CyrillicMicroScore& s
) const noexcept {
    double total_bpv = 0.0;
    for (int i = 0; i < ru::ALPHA_SIZE; ++i) total_bpv += s.letter_totals[i];
    if (total_bpv < 1.0) total_bpv = 1.0;

    // Six-axis psychological mapping for Cyrillic:
    //   anxiety    → Н(14) + С(18)  nasal + sibilant tension  [mirrors S+N in Latin]
    //   attention  → А(0)  + К(11)  open vowel + sharp plosive [mirrors A+K in Latin]
    //   emotion    → М(13) + Ю(31)  weight + diphthong        [mirrors M+W in Latin]
    //   agitation  → Р(17) + З(8)   trill + sibilant          [mirrors R+Z in Latin]
    return MicroVector{
        .intensity  = s.raw_score / static_cast<double>(s.total_chars),
        .anxiety    = (s.letter_totals[14] + s.letter_totals[18]) / total_bpv * 100.0,
        .attention  = (s.letter_totals[ 0] + s.letter_totals[11]) / total_bpv * 100.0,
        .emotion    = (s.letter_totals[13] + s.letter_totals[31]) / total_bpv * 100.0,
        .agitation  = (s.letter_totals[17] + s.letter_totals[ 8]) / total_bpv * 100.0,
        .complexity = static_cast<double>(s.words_with_visual_complexity),
    };
}

void CyrillicOrthographicEngine::fill_telemetry(
    const CyrillicMicroScore& ms,
    WindowResult&             wr
) const {
    // Top-5 Cyrillic letters by raw frequency
    struct Entry { int idx; int count; };
    Entry entries[ru::ALPHA_SIZE];
    for (int i = 0; i < ru::ALPHA_SIZE; ++i)
        entries[i] = { i, ms.char_counts[i] };

    std::partial_sort(
        entries,
        entries + std::min(5, ru::ALPHA_SIZE),
        entries + ru::ALPHA_SIZE,
        [](const Entry& a, const Entry& b) { return a.count > b.count; }
    );

    for (int i = 0; i < 5; ++i) {
        if (entries[i].count == 0) break;
        wr.top_micro_chars[ru::RU_GLYPH[entries[i].idx]] = entries[i].count;
    }

    // Double-letter anomalies (e.g. "СС", "ЛЛ")
    for (int i = 0; i < ru::ALPHA_SIZE; ++i) {
        if (ms.double_letter_counts[i] > 0) {
            std::string pair =
                std::string(ru::RU_GLYPH[i]) + ru::RU_GLYPH[i];
            wr.double_letter_anomalies[pair] = ms.double_letter_counts[i];
        }
    }
}


// ===========================================================================
// Private: score_word
// ===========================================================================

void CyrillicOrthographicEngine::score_word(
    const int*          indices,
    int                 n,
    CyrillicMicroScore& out
) const noexcept {
    double contributions[MAX_WORD] = {};
    bool   consumed[MAX_WORD]      = {};

    // Pass A — double-letter Gm (Rule 4)
    pass_double_letters(indices, n, contributions, consumed, out.double_letter_counts);

    // Pass B — interaction coefficient pairs (Rule 5)
    pass_interactions(indices, n, contributions, consumed);

    // Pass C — standard positional scoring (Rules 1–3) + visual complexity
    double word_score = 0.0;
    for (int i = 0; i < n; ++i) word_score += contributions[i];

    bool has_visual = false;

    for (int i = 0; i < n; ++i) {
        const int idx = indices[i];
        if (idx < 0 || idx >= ru::ALPHA_SIZE) continue;

        if (ru::is_visual_anchor_ru(idx)) has_visual = true;

        out.letter_totals[idx] += static_cast<double>(ru::bpv_ru(idx));
        out.char_counts[idx]++;

        if (!consumed[i]) {
            const uint8_t b = ru::bpv_ru(idx);
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

void CyrillicOrthographicEngine::pass_double_letters(
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
            const double gm   = ru::double_gm_ru(idx);
            const double half = static_cast<double>(ru::bpv_ru(idx)) * gm / 2.0;

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

void CyrillicOrthographicEngine::pass_interactions(
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

            const ru::CyrillicInteractionCoeff* coeff =
                ru::find_interaction_ru(ia, ib);
            if (!coeff) continue;

            const double p_d = (b - a == 1) ? 1.0 : 0.5;
            const double pair_score =
                (static_cast<double>(ru::bpv_ru(ia)) +
                 static_cast<double>(ru::bpv_ru(ib)))
                * coeff->ic * p_d;

            if (!consumed[a]) { contributions[a] += pair_score / 2.0; consumed[a] = true; }
            if (!consumed[b]) { contributions[b] += pair_score / 2.0; consumed[b] = true; }
        }
    }
}

} // namespace psycho
