#pragma once
/**
 * types.h
 * -------
 * Shared data structures consumed by every module in the psycho_core library.
 * No implementations — pure POD / aggregate types only.
 *
 * v2 additions (Raw Telemetry upgrade):
 *   MicroScore  — char_counts[26], total_words, double_letter_counts[26]
 *   WindowResult — total_chars, total_words, avg_word_length,
 *                  top_micro_chars, double_letter_anomalies
 *
 * v3 additions (Localization Tracking):
 *   TextWindow   — start_line, end_line (1-based line numbers in source document)
 *   WindowResult — start_line, end_line, start_snippet, end_snippet
 */

#include <map>
#include <string>
#include <string_view>
#include <vector>
#include <cstdint>

namespace psycho {

// ---------------------------------------------------------------------------
// Six-vector micro output
// Matches Python MicroResult.vectors keys exactly.
// All values are normalized (intensity = raw/chars; others = % of total BPV).
// ---------------------------------------------------------------------------
struct MicroVector {
    double intensity  = 0.0;   // raw_score / total_chars
    double anxiety    = 0.0;   // (S + N) / total_bpv * 100
    double attention  = 0.0;   // (A + K) / total_bpv * 100
    double emotion    = 0.0;   // (M + W) / total_bpv * 100
    double agitation  = 0.0;   // (R + Z) / total_bpv * 100
    double complexity = 0.0;   // count of words containing W, M, or K
};

// ---------------------------------------------------------------------------
// Internal rich scoring state accumulated during one window pass.
// All arrays are indexed by (letter - 'A'), so A=0, B=1, … Z=25.
// Fixed-size arrays keep the hot loop allocation-free.
// ---------------------------------------------------------------------------
struct MicroScore {
    double raw_score                    = 0.0;
    int    total_chars                  = 0;   // total alpha chars across all words
    int    total_words                  = 0;   // word count in this window
    double letter_totals[26]            = {};  // BPV-weighted per-letter sum
    int    char_counts[26]              = {};  // raw character frequency (unweighted)
    int    double_letter_counts[26]     = {};  // occurrences of each XX double-pair
    int    words_with_visual_complexity = 0;
};

// ---------------------------------------------------------------------------
// One zero-copy window view produced by the rolling window engine.
// TextWindow::text is a std::string_view into the original document buffer.
// ---------------------------------------------------------------------------
struct TextWindow {
    int              index        = 0;
    std::string_view text;                      // view into the original buffer
    std::size_t      start_char   = 0;          // absolute offset in source
    std::size_t      end_char     = 0;          // absolute offset in source
    std::string      reset_reason = "stride";   // "stride" | "structural_boundary"
    int              start_line   = 1;          // 1-based line number of start_char in the source document
    int              end_line     = 1;          // 1-based line number of end_char in the source document
};

// ---------------------------------------------------------------------------
// Full result for one window: metadata + normalized vectors + raw telemetry.
// Populated by bindings.cpp::run_pipeline(); serialized to a Python dict.
//
// top_micro_chars        : top-5 characters by raw occurrence count
// double_letter_anomalies: every XX double-pair found and its count
// macro_drivers          : intentionally left empty here — populated by the
//                          Python layer (routes.py) after spaCy macro analysis
// ---------------------------------------------------------------------------
struct WindowResult {
    // ── Identity ────────────────────────────────────────────────────────────
    int         index        = 0;
    std::size_t start_char   = 0;
    std::size_t end_char     = 0;
    std::string reset_reason = "stride";

    // ── Spatial Localization ──────────────────────────────────────────────────
    int         start_line    = 1;   // 1-based line number of window start in source
    int         end_line      = 1;   // 1-based line number of window end in source
    std::string start_snippet;       // first ~60 chars, trimmed to word boundary
    std::string end_snippet;         // last ~60 chars, trimmed to word boundary

    // ── Normalized six-vector output ─────────────────────────────────────────
    MicroVector vectors;

    // ── Raw telemetry ────────────────────────────────────────────────────────
    int   total_chars     = 0;
    int   total_words     = 0;
    float avg_word_length = 0.0f;

    // Top-5 letters by raw frequency: {"E": 42, "S": 38, …}
    std::map<std::string, int> top_micro_chars;

    // Double-letter pairs found: {"SS": 3, "LL": 1, …}
    std::map<std::string, int> double_letter_anomalies;

    // Optional stroke-count waveform injected by Python for logographic languages.
    // Empty for Latin-script windows; populated by analyze_with_strokes() for ZH.
    std::vector<int> structural_waveform;

    // ── v3.3: Steganographic anomaly detection ───────────────────────────────
    // hidden_unicode_count: ZW-space/ZWNJ/ZWJ/Word-Joiner/BOM occurrences +
    //   trailing whitespace chars (space/tab before newline — binary pacing cue)
    int  hidden_unicode_count = 0;
    bool stego_anomaly_flag   = false;   // true when hidden_unicode_count > 0

    // ── v3.3: Punctuation structural waveform ───────────────────────────────
    // Ordered magnitude values for every punctuation mark in the window:
    //   ','=1  '.'=2  ':'=2  '-'=2  en-dash=2  ';'=3  em-dash=3  '!'=4  '?'=4
    // Maps syntactic pause strength; sparse waveform encodes "Morse pacing".
    std::vector<int> punctuation_waveform;
};

} // namespace psycho
