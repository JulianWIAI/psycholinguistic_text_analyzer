/**
 * bindings.cpp
 * ------------
 * pybind11 Python module for the C++ micro-layer core.
 *
 * v2 additions (Raw Telemetry):
 *   window_result_to_dict() now serializes a nested "raw_telemetry" dict:
 *     total_chars, total_words, avg_word_length,
 *     top_micro_chars (top-5 by raw count),
 *     double_letter_anomalies (XX → count),
 *     macro_drivers (empty dict — populated by Python routes.py after spaCy).
 *
 * Exported functions
 * ──────────────────
 * analyze(text, window_size, stride)
 *     Single-document micro-layer pipeline.
 *     Returns list[dict] — one dict per window; see window_result_to_dict().
 *
 * analyze_sections_parallel(sections, window_size, stride, n_threads)
 *     Chapter-level parallelism via ThreadPool.
 *     Returns list[list[dict]].
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "window_engine.h"
#include "micro_analyzer.h"
#include "thread_pool.h"
#include "types.h"

#include <algorithm>
#include <array>
#include <string>
#include <vector>
#include <future>

namespace py = pybind11;
using namespace psycho;


// ---------------------------------------------------------------------------
// Convert MicroVector → Python dict (six canonical keys)
// ---------------------------------------------------------------------------
static py::dict vectors_to_dict(const MicroVector& v) {
    py::dict d;
    d["intensity"]  = v.intensity;
    d["anxiety"]    = v.anxiety;
    d["attention"]  = v.attention;
    d["emotion"]    = v.emotion;
    d["agitation"]  = v.agitation;
    d["complexity"] = v.complexity;
    return d;
}


// ---------------------------------------------------------------------------
// Convert WindowResult → Python dict (all fields including raw telemetry)
// ---------------------------------------------------------------------------
static py::dict window_result_to_dict(const WindowResult& wr) {
    py::dict d;
    d["index"]        = wr.index;
    d["start_char"]   = wr.start_char;
    d["end_char"]     = wr.end_char;
    d["reset_reason"] = wr.reset_reason;
    d["vectors"]      = vectors_to_dict(wr.vectors);

    // ── Raw telemetry nested dict ───────────────────────────────────────────
    py::dict telem;
    telem["total_chars"]     = wr.total_chars;
    telem["total_words"]     = wr.total_words;
    telem["avg_word_length"] = wr.avg_word_length;

    // Top-5 letters by raw character frequency
    py::dict top_chars;
    for (const auto& [letter, count] : wr.top_micro_chars) {
        top_chars[letter.c_str()] = count;
    }
    telem["top_micro_chars"] = top_chars;

    // Double-letter pair anomalies
    py::dict dl_anom;
    for (const auto& [pair, count] : wr.double_letter_anomalies) {
        dl_anom[pair.c_str()] = count;
    }
    telem["double_letter_anomalies"] = dl_anom;

    // macro_drivers is left empty here; the Python API layer (routes.py)
    // fills it after running the spaCy macro analyzer.
    telem["macro_drivers"] = py::dict();

    d["raw_telemetry"] = telem;
    return d;
}


// ---------------------------------------------------------------------------
// Core pipeline: text → vector<WindowResult>
// ---------------------------------------------------------------------------
static std::vector<WindowResult> run_pipeline(
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
        // Run the full scoring pass; keep the rich MicroScore for telemetry.
        const MicroScore ms = scorer.score_window(win.text);

        WindowResult wr;
        wr.index        = win.index;
        wr.start_char   = win.start_char;
        wr.end_char     = win.end_char;
        wr.reset_reason = win.reset_reason;
        wr.vectors      = scorer.to_vectors(ms);

        // ── Populate raw telemetry ──────────────────────────────────────────
        wr.total_chars     = ms.total_chars;
        wr.total_words     = ms.total_words;
        wr.avg_word_length = ms.total_words > 0
            ? static_cast<float>(ms.total_chars) / static_cast<float>(ms.total_words)
            : 0.0f;

        // Top-5 characters by raw frequency: sort descending, take 5.
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

        // Double-letter anomalies: any letter whose count > 0.
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


// ---------------------------------------------------------------------------
// Exported: analyze — single document
// ---------------------------------------------------------------------------
static py::list analyze(
    const std::string& text,
    int                window_size = 1000,
    int                stride      = 500
) {
    std::vector<WindowResult> results;
    {
        py::gil_scoped_release release;
        results = run_pipeline(text, window_size, stride);
    }

    py::list out;
    for (const auto& wr : results) {
        out.append(window_result_to_dict(wr));
    }
    return out;
}


// ---------------------------------------------------------------------------
// Exported: analyze_sections_parallel — chapter-level parallelism
// ---------------------------------------------------------------------------
static py::list analyze_sections_parallel(
    const std::vector<std::string>& sections,
    int                              window_size = 1000,
    int                              stride      = 500,
    std::size_t                      n_threads   = 0
) {
    if (n_threads == 0) {
        n_threads = std::thread::hardware_concurrency();
        if (n_threads == 0) n_threads = 4;
    }

    std::vector<std::future<std::vector<WindowResult>>> futures;
    futures.reserve(sections.size());

    {
        py::gil_scoped_release release;

        ThreadPool pool(std::min(n_threads, sections.size()));
        for (const auto& sec : sections) {
            futures.push_back(
                pool.submit([sec, window_size, stride]() -> std::vector<WindowResult> {
                    return run_pipeline(sec, window_size, stride);
                })
            );
        }
        pool.wait_all();
    }

    py::list outer;
    for (auto& fut : futures) {
        py::list inner;
        for (const auto& wr : fut.get()) {
            inner.append(window_result_to_dict(wr));
        }
        outer.append(inner);
    }
    return outer;
}


// ===========================================================================
// Module
// ===========================================================================
PYBIND11_MODULE(psycho_core, m) {
    m.doc() = R"pbdoc(
        psycho_core v2 — compiled BPV orthographic engine with raw telemetry.
        Exports: analyze(), analyze_sections_parallel()
    )pbdoc";

    m.def("analyze", &analyze,
        py::arg("text"),
        py::arg("window_size") = 1000,
        py::arg("stride")      = 500,
        R"pbdoc(
            Tokenize *text* and score each window with the BPV pipeline.
            Returns list[dict]; each dict contains:
              index, start_char, end_char, reset_reason, vectors,
              raw_telemetry: {
                total_chars, total_words, avg_word_length,
                top_micro_chars, double_letter_anomalies, macro_drivers
              }
        )pbdoc"
    );

    m.def("analyze_sections_parallel", &analyze_sections_parallel,
        py::arg("sections"),
        py::arg("window_size") = 1000,
        py::arg("stride")      = 500,
        py::arg("n_threads")   = 0,
        "Process multiple sections in parallel. Returns list[list[dict]]."
    );

    m.attr("DEFAULT_WINDOW_SIZE") = 1000;
    m.attr("DEFAULT_STRIDE")      = 500;
    m.attr("VERSION")             = "2.0.0";
}
