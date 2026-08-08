#pragma once
/**
 * somatic_analyzer.h — Main Somatic/Archetypal Cipher analyzer.
 *
 * Provides two operations:
 *   analyze()               — Per-window: word scoring, FFT, micro oscilloscope.
 *   compute_global_envelope()— Whole-document: 100-bucket energy envelope for
 *                             the "Global Waveform" chart.
 */

#include "types.h"
#include <string>
#include <vector>
#include <optional>

namespace psycho {

class SomaticAnalyzer {
public:
    SomaticAnalyzer() = default;

    /**
     * Analyze a single text window.
     *
     * Returns a WindowResult containing:
     *   - Per-word scatter data (word_sum, sigma, digital_root, category, tier)
     *   - Category and tier distributions / scores
     *   - micro_wavelength: first 256 letter values (0-padded to exactly 256)
     *   - top_harmonics:    top 5 FFT peaks from the 256-sample array
     */
    WindowResult analyze(const std::string& text) const;

    /**
     * Compute the Global Waveform Envelope for an entire document.
     *
     * Divides all valid letter values in *text* into *n_buckets* equal-size
     * bins and returns the mean value of each bin.  Designed to compress even
     * book-length text into a fixed 100-float summary for the UI chart.
     *
     * @param text      Full document text (UTF-8).
     * @param n_buckets Number of output buckets (default: 100).
     */
    std::vector<float> compute_global_envelope(
        const std::string& text,
        int n_buckets = 100
    ) const;

private:
    // ── Internal word scorer ─────────────────────────────────────────────────
    /** Score one UTF-8 word (already uppercased). Returns nullopt if no
     *  known letters are found. */
    std::optional<WordResult> score_word(const std::string& upper_word) const;

    // ── UTF-8 letter iterator ────────────────────────────────────────────────
    /**
     * Walk a UTF-8 string and collect (value, category_ptr) pairs for every
     * letter that has a non-zero entry in the lookup table.
     */
    struct LetterEntry { float value; const char* category; };
    std::vector<LetterEntry> extract_letters(const std::string& utf8_upper) const;

    // ── Tokenizer ────────────────────────────────────────────────────────────
    /** Split UTF-8 text into upper-cased letter-run tokens. */
    std::vector<std::string> tokenize(const std::string& text) const;

    // ── Math helpers ─────────────────────────────────────────────────────────
    static float pop_sigma(const std::vector<float>& values);
    static int   digital_root(int n);
};

} // namespace psycho
