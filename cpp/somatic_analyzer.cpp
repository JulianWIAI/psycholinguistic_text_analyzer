/**
 * somatic_analyzer.cpp — Core implementation of the Somatic/Archetypal Cipher.
 *
 * Depends on:
 *   letter_table.h/cpp — numeric value + category lookup
 *   fft.h/cpp          — Radix-2 Cooley-Tukey FFT
 *   types.h            — WordResult, SpectralPeak, WindowResult
 */

#include "somatic_analyzer.h"
#include "letter_table.h"
#include "fft.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <map>
#include <numeric>
#include <unordered_map>

namespace psycho {

// ════════════════════════════════════════════════════════════════════════════
// Math helpers
// ════════════════════════════════════════════════════════════════════════════

float SomaticAnalyzer::pop_sigma(const std::vector<float>& values) {
    const std::size_t n = values.size();
    if (n < 2) return 0.f;
    const float mean = std::accumulate(values.begin(), values.end(), 0.f) / n;
    float var = 0.f;
    for (float v : values) var += (v - mean) * (v - mean);
    return std::sqrt(var / static_cast<float>(n));
}

int SomaticAnalyzer::digital_root(int n) {
    // 9-complement shortcut: dr(n) = 1 + (n-1) % 9  for n > 0
    if (n <= 0) return 0;
    int r = n % 9;
    return r == 0 ? 9 : r;
}

// ════════════════════════════════════════════════════════════════════════════
// UTF-8 tokenizer — produces uppercase letter-run words
// ════════════════════════════════════════════════════════════════════════════

std::vector<std::string> SomaticAnalyzer::tokenize(const std::string& text) const {
    std::vector<std::string> words;
    std::string current;

    auto flush = [&]() {
        if (!current.empty()) { words.push_back(current); current.clear(); }
    };

    for (std::size_t i = 0; i < text.size(); ) {
        const unsigned char c = static_cast<unsigned char>(text[i]);

        if (c < 0x80) {
            // ── ASCII ──────────────────────────────────────────────────────
            if (std::isalpha(c)) {
                current += static_cast<char>(std::toupper(c));
            } else {
                flush();
            }
            ++i;

        } else if (c == 0xC3 && i + 1 < text.size()) {
            // ── 2-byte UTF-8 with 0xC3 leader (covers Ä Ö Ü ä ö ü) ───────
            const unsigned char second = static_cast<unsigned char>(text[i + 1]);
            const LetterInfo info = lookup_umlaut(second);
            if (info.value > 0.f) {
                // Normalise to uppercase form in the token
                unsigned char upper_second = second;
                if (second == 0xA4) upper_second = 0x84;  // ä → Ä
                if (second == 0xB6) upper_second = 0x96;  // ö → Ö
                if (second == 0xBC) upper_second = 0x9C;  // ü → Ü
                current += static_cast<char>(0xC3);
                current += static_cast<char>(upper_second);
            } else {
                flush();
            }
            i += 2;

        } else {
            // ── Other multi-byte sequence — skip whole codepoint ───────────
            flush();
            ++i;
            while (i < text.size() &&
                   (static_cast<unsigned char>(text[i]) & 0xC0) == 0x80)
                ++i;
        }
    }
    flush();
    return words;
}

// ════════════════════════════════════════════════════════════════════════════
// Per-word letter extraction (returns ordered value+category pairs)
// ════════════════════════════════════════════════════════════════════════════

std::vector<SomaticAnalyzer::LetterEntry>
SomaticAnalyzer::extract_letters(const std::string& utf8_upper) const {
    std::vector<LetterEntry> out;
    out.reserve(utf8_upper.size());

    for (std::size_t i = 0; i < utf8_upper.size(); ) {
        const unsigned char c = static_cast<unsigned char>(utf8_upper[i]);

        if (c < 0x80) {
            const LetterInfo info = lookup_ascii(static_cast<char>(c));
            if (info.value > 0.f) out.push_back({ info.value, info.category });
            ++i;
        } else if (c == 0xC3 && i + 1 < utf8_upper.size()) {
            const unsigned char second = static_cast<unsigned char>(utf8_upper[i + 1]);
            const LetterInfo info = lookup_umlaut(second);
            if (info.value > 0.f) out.push_back({ info.value, info.category });
            i += 2;
        } else {
            ++i;
            while (i < utf8_upper.size() &&
                   (static_cast<unsigned char>(utf8_upper[i]) & 0xC0) == 0x80)
                ++i;
        }
    }
    return out;
}

// ════════════════════════════════════════════════════════════════════════════
// Score a single (uppercased) word
// ════════════════════════════════════════════════════════════════════════════

std::optional<WordResult>
SomaticAnalyzer::score_word(const std::string& upper_word) const {
    const auto entries = extract_letters(upper_word);
    if (entries.empty()) return std::nullopt;

    std::vector<float> vals;
    vals.reserve(entries.size());
    for (const auto& e : entries) vals.push_back(e.value);

    const float word_sum = std::accumulate(vals.begin(), vals.end(), 0.f);
    const float sigma    = pop_sigma(vals);
    const int   dr       = digital_root(static_cast<int>(std::round(word_sum)));

    // Dominant category (plurality vote)
    std::unordered_map<std::string, int> freq;
    for (const auto& e : entries) freq[e.category]++;
    std::string dom_cat;
    int dom_cnt = 0;
    for (const auto& [cat, cnt] : freq) {
        if (cnt > dom_cnt) { dom_cnt = cnt; dom_cat = cat; }
    }

    const int tier = (sigma < 2.f) ? 1 : (sigma < 5.f) ? 2 : 3;

    return WordResult{ upper_word, word_sum, sigma, dr, dom_cat, tier };
}

// ════════════════════════════════════════════════════════════════════════════
// analyze() — per-window entry point
// ════════════════════════════════════════════════════════════════════════════

WindowResult SomaticAnalyzer::analyze(const std::string& text) const {
    WindowResult result;

    const auto words = tokenize(text);
    if (words.empty()) return result;

    // ── Collect letter values for oscilloscope + FFT ─────────────────────
    std::vector<float> raw_signal;
    raw_signal.reserve(256);

    // ── Per-word statistics ───────────────────────────────────────────────
    std::map<int, int>                 qsum_counts;
    std::unordered_map<std::string, int> cat_letter_counts;
    float sigma_sum = 0.f;

    for (const auto& word : words) {
        auto wr = score_word(word);
        if (!wr) continue;

        result.word_scatter.push_back(*wr);
        result.tier_distribution[wr->tier]++;
        qsum_counts[wr->digital_root]++;
        sigma_sum += wr->sigma;

        // Accumulate letter values for oscilloscope (first 256 only)
        const auto entries = extract_letters(word);
        for (const auto& e : entries) {
            if (raw_signal.size() < 256) raw_signal.push_back(e.value);
            cat_letter_counts[e.category]++;
        }
    }

    const std::size_t n_words = result.word_scatter.size();
    if (n_words == 0) return result;

    // ── Pad micro_wavelength to exactly 256 ──────────────────────────────
    result.micro_wavelength.resize(256, 0.f);
    for (std::size_t i = 0; i < raw_signal.size(); ++i)
        result.micro_wavelength[i] = raw_signal[i];

    // ── FFT on the 256-sample micro array ────────────────────────────────
    result.top_harmonics = dominant_harmonics(result.micro_wavelength, 256, 5);

    // ── Aggregates ───────────────────────────────────────────────────────
    result.avg_word_sigma = sigma_sum / static_cast<float>(n_words);

    // Modal quersumme
    int best_qs = 0, best_cnt = 0;
    for (const auto& [qs, cnt] : qsum_counts) {
        if (cnt > best_cnt) { best_cnt = cnt; best_qs = qs; }
    }
    result.dominant_quersumme = best_qs;

    // Category letter counts → category_counts field
    for (const auto& [k, v] : cat_letter_counts)
        result.category_counts[k] = v;

    // Category fractions
    int total_letters = 0;
    for (const auto& [_, v] : cat_letter_counts) total_letters += v;
    if (total_letters > 0) {
        const float tl = static_cast<float>(total_letters);
        auto get = [&](const std::string& k) -> float {
            auto it = cat_letter_counts.find(k);
            return it != cat_letter_counts.end() ? it->second / tl : 0.f;
        };
        result.somatic_score     = get("origin");
        result.sovereignty_score = get("sovereign");
        result.resonant_score    = get("resonant");
        result.kinetic_score     = get("kinetic");
        result.liminal_score     = get("liminal");
    }

    return result;
}

// ════════════════════════════════════════════════════════════════════════════
// compute_global_envelope() — full-document 100-bucket energy envelope
// ════════════════════════════════════════════════════════════════════════════

std::vector<float>
SomaticAnalyzer::compute_global_envelope(const std::string& text, int n_buckets) const {
    // ── Extract ALL letter values from the full document ──────────────────
    std::vector<float> all_values;
    all_values.reserve(8192);

    for (std::size_t i = 0; i < text.size(); ) {
        const unsigned char c = static_cast<unsigned char>(text[i]);

        if (c < 0x80) {
            const LetterInfo info = lookup_ascii(static_cast<char>(std::toupper(c)));
            if (info.value > 0.f) all_values.push_back(info.value);
            ++i;
        } else if (c == 0xC3 && i + 1 < text.size()) {
            const unsigned char second = static_cast<unsigned char>(text[i + 1]);
            const LetterInfo info = lookup_umlaut(second);
            if (info.value > 0.f) all_values.push_back(info.value);
            i += 2;
        } else {
            ++i;
            while (i < text.size() &&
                   (static_cast<unsigned char>(text[i]) & 0xC0) == 0x80)
                ++i;
        }
    }

    // ── Divide into n_buckets equal-size bins, compute mean per bin ───────
    std::vector<float> envelope(n_buckets, 0.f);
    const std::size_t total = all_values.size();
    if (total == 0) return envelope;

    for (int b = 0; b < n_buckets; ++b) {
        // Map bucket b to the [start, end) range of all_values
        const std::size_t start = (b * total) / n_buckets;
        const std::size_t end   = ((b + 1) * total) / n_buckets;
        if (start >= end) continue;

        float sum = 0.f;
        for (std::size_t i = start; i < end; ++i) sum += all_values[i];
        envelope[b] = sum / static_cast<float>(end - start);
    }

    return envelope;
}

} // namespace psycho
