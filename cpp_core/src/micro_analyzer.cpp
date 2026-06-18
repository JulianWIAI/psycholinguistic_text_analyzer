/**
 * micro_analyzer.cpp
 * ------------------
 * Full five-rule BPV orthographic scoring pipeline.
 * Exact numerical parity with micro_layer/orthographic_analyzer.py.
 *
 * v2 additions (Raw Telemetry):
 *   score_window() — increments out.total_words per word found.
 *   score_word()   — accumulates out.char_counts[ch-'A'] for every char,
 *                    passes out.double_letter_counts to pass_double_letters.
 *   pass_double_letters() — increments dl_counts[c-'A'] for each XX pair.
 *
 * All new accounting is zero-overhead: it piggybacks on the existing
 * character loops with no extra iterations.
 */

#include "micro_analyzer.h"
#include <cctype>
#include <algorithm>
#include <cstring>

namespace psycho {

// ===========================================================================
// Public interface
// ===========================================================================

MicroVector OrthographicEngine::analyze(std::string_view text) const {
    return to_vectors(score_window(text));
}

MicroScore OrthographicEngine::score_window(std::string_view text) const {
    MicroScore out{};

    char word_buf[MAX_WORD + 1];
    int  word_len = 0;

    const std::size_t n = text.size();
    for (std::size_t i = 0; i <= n; ++i) {
        const bool is_alpha =
            (i < n) && std::isalpha(static_cast<unsigned char>(text[i]));

        if (is_alpha) {
            if (word_len < MAX_WORD) {
                word_buf[word_len] =
                    static_cast<char>(std::toupper(static_cast<unsigned char>(text[i])));
            }
            ++word_len;
        } else if (word_len > 0) {
            word_len           = std::min(word_len, MAX_WORD);
            word_buf[word_len] = '\0';
            out.total_chars   += word_len;
            out.total_words++;                  // count every word found
            score_word(word_buf, word_len, out);
            word_len = 0;
        }
    }

    if (out.total_chars == 0) out.total_chars = 1;
    return out;
}

MicroVector OrthographicEngine::to_vectors(const MicroScore& s) const noexcept {
    double total_bpv = 0.0;
    for (int i = 0; i < 26; ++i) total_bpv += s.letter_totals[i];
    if (total_bpv < 1.0) total_bpv = 1.0;

    // Letter indices (letter - 'A'):  A=0 K=10 M=12 N=13 R=17 S=18 W=22 Z=25
    return MicroVector{
        .intensity  = s.raw_score / static_cast<double>(s.total_chars),
        .anxiety    = (s.letter_totals[18] + s.letter_totals[13]) / total_bpv * 100.0,
        .attention  = (s.letter_totals[0]  + s.letter_totals[10]) / total_bpv * 100.0,
        .emotion    = (s.letter_totals[12] + s.letter_totals[22]) / total_bpv * 100.0,
        .agitation  = (s.letter_totals[17] + s.letter_totals[25]) / total_bpv * 100.0,
        .complexity = static_cast<double>(s.words_with_visual_complexity),
    };
}


// ===========================================================================
// Private: score_word
// ===========================================================================

void OrthographicEngine::score_word(
    const char* word,
    int         n,
    MicroScore& out
) const noexcept {
    double contributions[MAX_WORD] = {};
    bool   consumed[MAX_WORD]      = {};

    // ── Pass A: double-letter Gm (Rule 4) ────────────────────────────────
    // Passes out.double_letter_counts so each XX pair is tallied.
    pass_double_letters(word, n, contributions, consumed, out.double_letter_counts);

    // ── Pass B: interaction coefficient pairs (Rule 5) ───────────────────
    pass_interactions(word, n, contributions, consumed);

    // ── Pass C: standard positional scoring (Rules 1–3) ──────────────────
    double word_score = 0.0;
    for (int i = 0; i < n; ++i)
        word_score += contributions[i];

    bool has_visual = false;

    for (int i = 0; i < n; ++i) {
        const unsigned char ch = static_cast<unsigned char>(word[i]);

        if (is_visual_anchor(ch)) has_visual = true;

        // Accumulate BPV-weighted letter total AND raw char count in one pass.
        if (ch >= 'A' && ch <= 'Z') {
            out.letter_totals[ch - 'A'] += static_cast<double>(bpv(ch));
            out.char_counts[ch - 'A']++;        // raw frequency for telemetry
        }

        if (!consumed[i]) {
            const uint8_t b = bpv(ch);
            if (b == 0) continue;
            const double pos_mult = (i == 0)     ? POS_START
                                  : (i == n - 1) ? POS_END
                                                 : POS_MIDDLE;
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

void OrthographicEngine::pass_double_letters(
    const char* word,
    int         n,
    double*     contributions,
    bool*       consumed,
    int*        dl_counts       // MicroScore::double_letter_counts[26]
) const noexcept {
    int i = 0;
    while (i < n - 1) {
        if (word[i] == word[i + 1]) {
            const unsigned char c  = static_cast<unsigned char>(word[i]);
            const double        gm = double_gm(c);
            const double half = static_cast<double>(bpv(c)) * gm / 2.0;

            contributions[i]     = half;
            contributions[i + 1] = half;
            consumed[i]          = true;
            consumed[i + 1]      = true;

            // Record this XX pair occurrence for the telemetry layer.
            if (c >= 'A' && c <= 'Z') {
                dl_counts[c - 'A']++;
            }

            i += 2;
        } else {
            ++i;
        }
    }
}


// ===========================================================================
// Private: pass_interactions  (Rule 5)
// ===========================================================================

void OrthographicEngine::pass_interactions(
    const char* word,
    int         n,
    double*     contributions,
    bool*       consumed
) const noexcept {
    for (int a = 0; a < n; ++a) {
        const int b_limit = std::min(a + 3, n);
        for (int b = a + 1; b < b_limit; ++b) {
            const unsigned char ca = static_cast<unsigned char>(word[a]);
            const unsigned char cb = static_cast<unsigned char>(word[b]);

            const InteractionCoeff* coeff = find_interaction(ca, cb);
            if (!coeff) continue;

            const double p_d        = (b - a == 1) ? 1.0 : 0.5;
            const double pair_score =
                (static_cast<double>(bpv(ca)) + static_cast<double>(bpv(cb)))
                * coeff->ic * p_d;

            if (!consumed[a]) {
                contributions[a] += pair_score / 2.0;
                consumed[a]       = true;
            }
            if (!consumed[b]) {
                contributions[b] += pair_score / 2.0;
                consumed[b]       = true;
            }
        }
    }
}

} // namespace psycho
