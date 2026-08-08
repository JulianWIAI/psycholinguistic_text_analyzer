#pragma once
/**
 * types.h — Core data structures for the Somatic/Archetypal Cipher C++ engine.
 *
 * All structs are plain data (no virtual methods) so pybind11 can bind them
 * trivially and they can be freely moved across translation units.
 */

#include <string>
#include <vector>
#include <map>

namespace psycho {

// ── Per-word output ──────────────────────────────────────────────────────────
struct WordResult {
    std::string word;              // Uppercased word as processed
    float       word_sum    = 0.f; // Σ numeric letter values
    float       sigma       = 0.f; // Population standard deviation
    int         digital_root = 0;  // Quersumme 1–9
    std::string dominant_category; // "origin"|"kinetic"|"resonant"|"sovereign"|"liminal"
    int         tier        = 1;   // 1=Somatic, 2=Archetypal Bridge, 3=State/System
};

// ── Single FFT spectral peak ─────────────────────────────────────────────────
struct SpectralPeak {
    int   bin       = 0;    // FFT bin index (1-based; 0=DC excluded)
    float magnitude = 0.f;  // |X[bin]| — complex magnitude
    float norm_freq = 0.f;  // bin / N_FFT  (normalised frequency, 0..0.5)
};

// ── Per-window aggregate output ──────────────────────────────────────────────
struct WindowResult {
    // ── Aggregate scalars ────────────────────────────────────────────────────
    float avg_word_sigma     = 0.f;  // Mean σ across all scored words
    int   dominant_quersumme = 0;    // Modal digital root
    float sovereignty_score  = 0.f;  // Fraction of Sovereign letters (D I K Q T W X Z)
    float somatic_score      = 0.f;  // Fraction of Origin letters (A only)
    float resonant_score     = 0.f;  // Fraction of Resonant letters (C H L M O U Y)
    float kinetic_score      = 0.f;  // Fraction of Kinetic letters  (B E F J P S V)
    float liminal_score      = 0.f;  // Fraction of Liminal letters  (Ä G N R Ö Ü)

    // ── Tier / category distributions ────────────────────────────────────────
    std::map<int, int>         tier_distribution;  // {1,2,3} → word count
    std::map<std::string, int> category_counts;    // category name → letter count

    // ── Word-level scatter payload (for Chart.js scatter plot) ───────────────
    std::vector<WordResult>   word_scatter;

    // ── Spectral / oscilloscope payloads ────────────────────────────────────
    std::vector<float>        micro_wavelength;  // First 256 valid letter values (0-padded)
    std::vector<SpectralPeak> top_harmonics;     // Top 5 non-DC FFT peaks
};

} // namespace psycho
