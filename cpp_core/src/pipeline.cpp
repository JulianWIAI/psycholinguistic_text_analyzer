/**
 * pipeline.cpp
 * ------------
 * Implementation of the shared single-document BPV scoring pipeline.
 *
 * Previously lived as a static helper inside bindings.cpp; extracted here
 * so that compare_engine.cpp can call it without duplicating the scoring
 * logic.
 */

#include "pipeline.h"
#include "window_engine.h"
#include "micro_analyzer.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <string>

namespace {

/// Extract first ~max_chars characters of sv, trimmed to a word boundary.
static std::string extract_start_snippet(std::string_view sv, std::size_t max_chars = 60) {
    if (sv.empty()) return {};
    // Skip leading whitespace
    std::size_t s = 0;
    while (s < sv.size() && std::isspace(static_cast<unsigned char>(sv[s]))) ++s;
    std::size_t e = std::min(s + max_chars, sv.size());
    // Walk back to a word boundary if we're not at the end
    if (e < sv.size()) {
        std::size_t wb = e;
        while (wb > s && !std::isspace(static_cast<unsigned char>(sv[wb - 1]))) --wb;
        if (wb > s) e = wb;
    }
    // Trim trailing whitespace
    while (e > s && std::isspace(static_cast<unsigned char>(sv[e - 1]))) --e;
    return std::string(sv.substr(s, e - s));
}

/// Extract last ~max_chars characters of sv, trimmed to a word boundary.
static std::string extract_end_snippet(std::string_view sv, std::size_t max_chars = 60) {
    if (sv.empty()) return {};
    // Trim trailing whitespace
    std::size_t e = sv.size();
    while (e > 0 && std::isspace(static_cast<unsigned char>(sv[e - 1]))) --e;
    std::size_t s = (e > max_chars) ? e - max_chars : 0;
    // Walk forward to a word boundary when we are not at the document start
    if (s > 0) {
        while (s < e && !std::isspace(static_cast<unsigned char>(sv[s]))) ++s;
        while (s < e &&  std::isspace(static_cast<unsigned char>(sv[s]))) ++s;
    }
    // Trim any remaining leading whitespace
    while (s < e && std::isspace(static_cast<unsigned char>(sv[s]))) ++s;
    return std::string(sv.substr(s, e - s));
}

// ---------------------------------------------------------------------------
// v3.3 — Hidden Unicode scanner
// Counts zero-width chars (U+200B/C/D, U+2060, U+FEFF) and trailing
// whitespace before newlines (space/tab used as binary pacing steganography).
// ---------------------------------------------------------------------------
static int count_hidden_unicode(std::string_view text) noexcept {
    int count = 0;
    const auto* s = reinterpret_cast<const unsigned char*>(text.data());
    const std::size_t n = text.size();
    for (std::size_t i = 0; i < n; ) {
        // 3-byte sequences beginning with E2
        if (i + 2 < n && s[i] == 0xE2) {
            // U+200B (E2 80 8B)  U+200C (E2 80 8C)  U+200D (E2 80 8D)
            if (s[i+1] == 0x80 && s[i+2] >= 0x8B && s[i+2] <= 0x8D) {
                ++count; i += 3; continue;
            }
            // U+2060 Word Joiner (E2 81 A0)
            if (s[i+1] == 0x81 && s[i+2] == 0xA0) {
                ++count; i += 3; continue;
            }
        }
        // U+FEFF BOM (EF BB BF)
        if (i + 2 < n && s[i] == 0xEF && s[i+1] == 0xBB && s[i+2] == 0xBF) {
            ++count; i += 3; continue;
        }
        // Trailing whitespace: run of spaces/tabs immediately before a newline
        if (s[i] == ' ' || s[i] == '\t') {
            std::size_t j = i;
            while (j < n && (s[j] == ' ' || s[j] == '\t')) ++j;
            if (j < n && s[j] == '\n') {
                count += static_cast<int>(j - i);
                i = j; continue;
            }
        }
        ++i;
    }
    return count;
}

// ---------------------------------------------------------------------------
// v3.3 — Punctuation structural waveform builder
// Returns an ordered array of pause-magnitude values for each punctuation mark.
// ---------------------------------------------------------------------------
static std::vector<int> build_punct_waveform(std::string_view text) {
    std::vector<int> wave;
    const auto* s = reinterpret_cast<const unsigned char*>(text.data());
    const std::size_t n = text.size();
    for (std::size_t i = 0; i < n; ) {
        const unsigned char c = s[i];
        if      (c == ',')              { wave.push_back(1); ++i; }
        else if (c == '.' || c == ':'
              || c == '-')             { wave.push_back(2); ++i; }
        else if (c == ';')             { wave.push_back(3); ++i; }
        else if (c == '!' || c == '?') { wave.push_back(4); ++i; }
        // En dash U+2013 (E2 80 93) → magnitude 2
        else if (i + 2 < n && c == 0xE2 && s[i+1] == 0x80 && s[i+2] == 0x93) {
            wave.push_back(2); i += 3;
        }
        // Em dash U+2014 (E2 80 94) → magnitude 3
        else if (i + 2 < n && c == 0xE2 && s[i+1] == 0x80 && s[i+2] == 0x94) {
            wave.push_back(3); i += 3;
        }
        else { ++i; }
    }
    return wave;
}

} // anonymous namespace

namespace psycho {

std::vector<WindowResult> run_pipeline(
    const std::string& text,
    int                window_size,
    int                stride
) {
    const RollingWindowEngine engine(window_size, stride);
    const OrthographicEngine  scorer;

    const auto windows = engine.tokenize(text);

    std::vector<WindowResult> results;
    results.reserve(windows.size());

    for (const auto& win : windows) {
        const MicroScore ms = scorer.score_window(win.text);

        WindowResult wr;
        wr.index        = win.index;
        wr.start_char   = win.start_char;
        wr.end_char     = win.end_char;
        wr.reset_reason = win.reset_reason;

        // ── Spatial localization ────────────────────────────────────────────
        wr.start_line    = win.start_line;
        wr.end_line      = win.end_line;
        wr.start_snippet = extract_start_snippet(win.text);
        wr.end_snippet   = extract_end_snippet(win.text);

        wr.vectors      = scorer.to_vectors(ms);

        wr.total_chars     = ms.total_chars;
        wr.total_words     = ms.total_words;
        wr.avg_word_length = ms.total_words > 0
            ? static_cast<float>(ms.total_chars) / static_cast<float>(ms.total_words)
            : 0.0f;

        // Top-5 characters by raw frequency
        struct LetterEntry { int idx; int count; };
        std::array<LetterEntry, 26> entries{};
        for (int i = 0; i < 26; ++i) entries[i] = { i, ms.char_counts[i] };

        std::partial_sort(
            entries.begin(),
            entries.begin() + std::min(5, 26),
            entries.end(),
            [](const LetterEntry& a, const LetterEntry& b) {
                return a.count > b.count;
            }
        );

        for (int i = 0; i < 5; ++i) {
            if (entries[i].count == 0) break;
            std::string letter(1, static_cast<char>('A' + entries[i].idx));
            wr.top_micro_chars[letter] = entries[i].count;
        }

        // Double-letter anomalies
        for (int i = 0; i < 26; ++i) {
            if (ms.double_letter_counts[i] > 0) {
                std::string pair(2, static_cast<char>('A' + i));
                wr.double_letter_anomalies[pair] = ms.double_letter_counts[i];
            }
        }

        // v3.3 — steganographic anomaly detection + punctuation waveform
        wr.hidden_unicode_count = count_hidden_unicode(win.text);
        wr.stego_anomaly_flag   = wr.hidden_unicode_count > 0;
        wr.punctuation_waveform = build_punct_waveform(win.text);

        results.push_back(std::move(wr));
    }

    return results;
}

} // namespace psycho
