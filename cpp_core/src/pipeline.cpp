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

        results.push_back(std::move(wr));
    }

    return results;
}

} // namespace psycho
