/**
 * bindings.cpp — pybind11 module exposing the Somatic Cipher C++ core.
 *
 * Module name: _somatic_core
 *
 * Exposed functions:
 *   analyze(text: str) -> dict
 *       Per-window analysis. Returns all word-level and spectral data.
 *
 *   compute_global_envelope(text: str, n_buckets: int = 100) -> list[float]
 *       Whole-document 100-bucket energy envelope for the Global Waveform chart.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "somatic_analyzer.h"

namespace py = pybind11;
using namespace psycho;

// ── Quersumme archetype strings (1–9) ────────────────────────────────────────
static const char* QUERSUMME_ARCH[10] = {
    "",                                                              // 0 unused
    "1 — Source: the undivided origin point, pure potential",
    "2 — Bond: duality and connection, the first relation",
    "3 — Overflow: creative expression spilling beyond containers",
    "4 — Foundation: law, structure, systemic stability",
    "5 — Friction: instability and kinetic transit between states",
    "6 — Grounding: harmonic equilibrium, aesthetic resolution",
    "7 — Precursor: the liminal threshold before emergence",
    "8 — Infinity/State: sovereign will, institutional recursion",
    "9 — Transcendent: full-cycle integration and dissolution",
};

// ── Tier metadata ─────────────────────────────────────────────────────────────
struct TierMeta { const char* code; const char* label; };
static constexpr TierMeta TIER[4] = {
    {"",   ""},                          // 0 unused
    {"T1", "Somatic / Universal"},
    {"T2", "Archetypal Bridge"},
    {"T3", "State / System"},
};

// ── Singleton analyzer (one per process, thread-safe for read-only analyze()) ─
static SomaticAnalyzer g_analyzer;

// ────────────────────────────────────────────────────────────────────────────
// analyze(text) → dict
// ────────────────────────────────────────────────────────────────────────────

py::dict py_analyze(const std::string& text) {
    const WindowResult wr = g_analyzer.analyze(text);

    // Determine dominant tier
    int dom_tier = 1, dom_cnt = 0;
    for (const auto& [t, c] : wr.tier_distribution) {
        if (c > dom_cnt) { dom_cnt = c; dom_tier = t; }
    }
    const TierMeta& tm = TIER[dom_tier];

    // Quersumme archetype
    const char* qs_arch = (wr.dominant_quersumme >= 1 && wr.dominant_quersumme <= 9)
        ? QUERSUMME_ARCH[wr.dominant_quersumme]
        : "";

    // Build word_scatter list-of-dicts
    py::list scatter;
    for (const auto& w : wr.word_scatter) {
        py::dict d;
        d["word"] = w.word;
        d["x"]    = std::round(w.word_sum * 100.f) / 100.f;
        d["y"]    = std::round(w.sigma    * 10000.f) / 10000.f;
        d["dr"]   = w.digital_root;
        d["cat"]  = w.dominant_category;
        d["tier"] = w.tier;
        scatter.append(d);
    }

    // Build top_harmonics list-of-dicts
    py::list harmonics;
    for (const auto& p : wr.top_harmonics) {
        py::dict h;
        h["bin"]       = p.bin;
        h["magnitude"] = std::round(p.magnitude * 10000.f) / 10000.f;
        h["norm_freq"] = std::round(p.norm_freq  * 1000000.f) / 1000000.f;
        harmonics.append(h);
    }

    // Build micro_wavelength list (256 floats, trailing zeros omitted by UI)
    py::list wavelength;
    for (float v : wr.micro_wavelength)
        wavelength.append(std::round(v * 1000.f) / 1000.f);

    // Build tier_distribution dict
    py::dict tier_dist;
    for (const auto& [t, c] : wr.tier_distribution)
        tier_dist[py::int_(t)] = c;

    // Build category_counts dict
    py::dict cat_counts;
    for (const auto& [k, v] : wr.category_counts)
        cat_counts[k.c_str()] = v;

    // Assemble result
    py::dict result;
    result["avg_word_sigma"]      = std::round(wr.avg_word_sigma     * 10000.f) / 10000.f;
    result["dominant_quersumme"]  = wr.dominant_quersumme;
    result["quersumme_archetype"] = qs_arch;
    result["sovereignty_score"]   = std::round(wr.sovereignty_score  * 10000.f) / 10000.f;
    result["somatic_score"]       = std::round(wr.somatic_score      * 10000.f) / 10000.f;
    result["resonant_score"]      = std::round(wr.resonant_score     * 10000.f) / 10000.f;
    result["kinetic_score"]       = std::round(wr.kinetic_score      * 10000.f) / 10000.f;
    result["liminal_score"]       = std::round(wr.liminal_score      * 10000.f) / 10000.f;
    result["tier_code"]           = tm.code;
    result["tier_label"]          = tm.label;
    result["tier_distribution"]   = tier_dist;
    result["category_counts"]     = cat_counts;
    result["word_scatter"]        = scatter;
    result["micro_wavelength"]    = wavelength;
    result["top_harmonics"]       = harmonics;

    return result;
}

// ────────────────────────────────────────────────────────────────────────────
// compute_global_envelope(text, n_buckets=100) → list[float]
// ────────────────────────────────────────────────────────────────────────────

py::list py_global_envelope(const std::string& text, int n_buckets) {
    const auto env = g_analyzer.compute_global_envelope(text, n_buckets);
    py::list out;
    for (float v : env)
        out.append(std::round(v * 10000.f) / 10000.f);
    return out;
}

// ────────────────────────────────────────────────────────────────────────────
// Module definition
// ────────────────────────────────────────────────────────────────────────────

PYBIND11_MODULE(_somatic_core, m) {
    m.doc() = R"doc(
        _somatic_core — Somatic/Archetypal Cipher C++ core (pybind11).

        Functions
        ---------
        analyze(text: str) -> dict
            Per-window psycholinguistic analysis including FFT spectral peaks.

        compute_global_envelope(text: str, n_buckets: int = 100) -> list[float]
            Compress entire document into a 100-bucket energy envelope.
    )doc";

    m.def("analyze", &py_analyze,
          py::arg("text"),
          "Analyze a text window; returns word stats + FFT harmonics + micro oscilloscope.");

    m.def("compute_global_envelope", &py_global_envelope,
          py::arg("text"), py::arg("n_buckets") = 100,
          "Compute 100-bucket global waveform envelope from the full document.");
}
