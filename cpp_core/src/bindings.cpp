/**
 * bindings.cpp
 * ------------
 * pybind11 Python module for the C++ micro-layer core.
 *
 * v3 additions (Compare Engine):
 *   compare_texts(text_a, text_b, window_size, stride)
 *     Parallel dual-text BPV analysis via CompareEngine.
 *     Returns dict { windows_a: list[dict], windows_b: list[dict],
 *                    alignments: list[dict] }
 *
 * v3.1 additions (Localization Tracking):
 *   Each window dict now includes: start_line, end_line, start_snippet, end_snippet.
 *
 * Exported functions
 * ──────────────────
 * analyze(text, window_size, stride)
 *     Single-document micro-layer pipeline.
 *     Returns list[dict] — one dict per window.
 *
 * analyze_sections_parallel(sections, window_size, stride, n_threads)
 *     Chapter-level parallelism via ThreadPool.
 *     Returns list[list[dict]].
 *
 * compare_texts(text_a, text_b, window_size, stride)
 *     Parallel dual-document analysis via CompareEngine.
 *     Returns dict with windows_a, windows_b, alignments.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "pipeline.h"
#include "compare_engine.h"
#include "thread_pool.h"
#include "types.h"

#include <algorithm>
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
    d["start_line"]     = wr.start_line;
    d["end_line"]       = wr.end_line;
    d["start_snippet"]  = wr.start_snippet;
    d["end_snippet"]    = wr.end_snippet;
    d["vectors"]      = vectors_to_dict(wr.vectors);

    // ── Raw telemetry nested dict ───────────────────────────────────────────
    py::dict telem;
    telem["total_chars"]     = wr.total_chars;
    telem["total_words"]     = wr.total_words;
    telem["avg_word_length"] = wr.avg_word_length;

    py::dict top_chars;
    for (const auto& [letter, count] : wr.top_micro_chars) {
        top_chars[letter.c_str()] = count;
    }
    telem["top_micro_chars"] = top_chars;

    py::dict dl_anom;
    for (const auto& [pair, count] : wr.double_letter_anomalies) {
        dl_anom[pair.c_str()] = count;
    }
    telem["double_letter_anomalies"] = dl_anom;

    telem["macro_drivers"] = py::dict();
    d["raw_telemetry"] = telem;
    return d;
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


// ---------------------------------------------------------------------------
// Exported: compare_texts — parallel dual-document analysis
// ---------------------------------------------------------------------------
static py::dict compare_texts(
    const std::string& text_a,
    const std::string& text_b,
    int                window_size = 1000,
    int                stride      = 500
) {
    CompareResult cr;
    {
        py::gil_scoped_release release;
        const CompareEngine engine(window_size, stride);
        cr = engine.compare(text_a, text_b);
    }

    py::list list_a;
    for (const auto& wr : cr.windows_a) {
        list_a.append(window_result_to_dict(wr));
    }

    py::list list_b;
    for (const auto& wr : cr.windows_b) {
        list_b.append(window_result_to_dict(wr));
    }

    py::list alignments;
    for (const auto& al : cr.alignments) {
        py::dict a;
        a["index_a"]        = al.index_a;
        a["index_b"]        = al.index_b;
        a["position_score"] = al.position_score;
        alignments.append(a);
    }

    py::dict result;
    result["windows_a"]  = list_a;
    result["windows_b"]  = list_b;
    result["alignments"] = alignments;
    return result;
}


// ===========================================================================
// Module
// ===========================================================================
PYBIND11_MODULE(psycho_core, m) {
    m.doc() = R"pbdoc(
        psycho_core v3.1 — compiled BPV orthographic engine with compare support and localization tracking.
        Exports: analyze(), analyze_sections_parallel(), compare_texts()
        Window dicts include: start_line, end_line, start_snippet, end_snippet.
    )pbdoc";

    m.def("analyze", &analyze,
        py::arg("text"),
        py::arg("window_size") = 1000,
        py::arg("stride")      = 500,
        R"pbdoc(
            Tokenize *text* and score each window with the BPV pipeline.
            Returns list[dict]; each dict: index, start_char, end_char,
            reset_reason, vectors, raw_telemetry.
        )pbdoc"
    );

    m.def("analyze_sections_parallel", &analyze_sections_parallel,
        py::arg("sections"),
        py::arg("window_size") = 1000,
        py::arg("stride")      = 500,
        py::arg("n_threads")   = 0,
        "Process multiple sections in parallel. Returns list[list[dict]]."
    );

    m.def("compare_texts", &compare_texts,
        py::arg("text_a"),
        py::arg("text_b"),
        py::arg("window_size") = 1000,
        py::arg("stride")      = 500,
        R"pbdoc(
            Analyse two documents in parallel using CompareEngine.
            Returns dict { windows_a: list[dict], windows_b: list[dict],
                           alignments: list[{index_a, index_b, position_score}] }
        )pbdoc"
    );

    m.attr("DEFAULT_WINDOW_SIZE") = 1000;
    m.attr("DEFAULT_STRIDE")      = 500;
    m.attr("VERSION")             = "3.1.0";
}
