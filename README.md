# PsychoLinguistic Analysis Engine v2

A real-time psycholinguistic profiling system that detects **steganographic layering**, **subconscious signal patterns**, and **authorial intent divergence** in text. Combines a compiled C++ orthographic core with spaCy vector-similarity macro analysis across five languages.

---

## Interface

![PsychoLinguistic Analysis Engine — Overview](docs/screenshot_overview.png)
*Micro-vector fingerprint radar, macro-cluster fingerprint, Z-score dashboard, and dissonance event log.*

![PsychoLinguistic Analysis Engine — Raw Telemetry](docs/screenshot_telemetry.png)
*Raw Telemetry drawer: Section A (structural baseline), Section B (frequency leaders + double-letter anomalies), Section C (driver matrix — all 12 macro poles with Z-scores and contributing lemmas).*

---

## What It Does

The engine runs every text window through two independent analysis layers and measures the divergence between them:

| Layer | What it measures |
|---|---|
| **Micro (subconscious)** | Orthographic pressure — how letters *look and sound* at a subconscious level, scored via Base Psychological Vectors (BPV) |
| **Macro (conscious)** | Semantic framing — which psychological clusters a text gravitates toward, scored via spaCy cosine similarity |
| **Dissonance Engine** | Statistical divergence (Z-score delta) between the two layers — flags where the author's *conscious framing* contradicts their *subconscious signal* |

A high dissonance delta indicates one of three conditions: **Posturing** (conscious framing exceeds subconscious intensity), **Suppressed Signal** (subconscious leaks past conscious framing), or **Psychological Fracture** (extreme divergence consistent with AI-generated or dissociated text).

---

## Features

- **5-language analysis** — English, German, Spanish, French, Japanese
- **C++ compiled micro-core** — pybind11 BPV engine with zero-copy window sliding, runs EN and DE
- **Vector similarity macro scoring** — spaCy `_md` models with cosine similarity against pre-built cluster centroids (25 seed words × 12 poles × 5 languages); falls back to exact-match on `_sm` models
- **Welford online baseline tracking** — running mean/σ per variable; statistically comparable Z-scores across documents
- **Author / Reader profile toggle** — Reader Profile inverts the Z-score space to model the psychological deficits the target audience brings to the text
- **Raw Telemetry drawer** — structural baseline (chars/words/avg length), BPV character frequency bars, double-letter anomaly chips, full 12-pole driver matrix
- **Bulk export** — JSON (full telemetry, all windows) and flat CSV (SPSS/R compatible)
- **Entity ledger** — persistent JSON database tracking baseline drift and dissonance event history across sessions
- **Rolling window tokenizer** — structural boundary detection (double newlines, chapter/section headings) with configurable window size and stride

---

## Architecture

```
psycholinguistic_text_analyzer/
├── main.py                        # FastAPI app entry point
├── api/
│   └── routes.py                  # REST endpoints + pipeline orchestration
├── language/
│   ├── router.py                  # Language factory + analyzer cache
│   └── registry.py                # spaCy model registry with _md/_sm fallback
├── micro_layer/
│   ├── base_analyzer.py           # MicroResult + BaseMicroAnalyzer ABC
│   ├── cpp_analyzer.py            # C++ adapter (EN, DE) with Python fallback
│   ├── orthographic_analyzer.py   # Python BPV pipeline (EN baseline)
│   ├── de_analyzer.py             # German: umlaut/ß normalisation → BPV
│   ├── es_analyzer.py             # Spanish: RR×2.0 / LL×1.5 overrides
│   ├── fr_analyzer.py             # French: silent terminal suppression
│   └── ja_analyzer.py             # Japanese: logographic matrix + Keigo
├── macro_layer/
│   ├── semantic_analyzer.py       # VectorClusterScorer + SemanticAnalyzer (EN)
│   ├── multilingual_analyzer.py   # Generic multilingual wrapper
│   ├── {en,de,es,fr,ja}_clusters.py  # 25 words × 12 poles per language
│   └── ja_clusters.py             # Also contains JapaneseSemanticAnalyzer + Keigo
├── dissonance/
│   └── engine.py                  # Welford stats + Z-scores + EMA + event detection
├── tokenizer/
│   └── rolling_window.py          # Structural boundary tokenizer
├── database/
│   └── schema.py                  # Entity JSON DB helpers
├── cpp_core/                      # C++20 pybind11 module
│   ├── include/
│   │   ├── types.h                # MicroScore, MicroVector, WindowResult
│   │   ├── bpv_table.h            # Compile-time BPV/Gm/interaction tables
│   │   ├── micro_analyzer.h
│   │   ├── window_engine.h
│   │   └── thread_pool.h
│   ├── src/
│   │   ├── micro_analyzer.cpp     # Five-rule BPV pipeline
│   │   ├── window_engine.cpp      # Zero-copy std::string_view window engine
│   │   ├── thread_pool.cpp        # C++20 std::jthread pool
│   │   └── bindings.cpp           # pybind11 exports
│   ├── CMakeLists.txt
│   └── build_release.bat          # One-click MSVC build script
├── templates/
│   └── index.html                 # Single-page analysis dashboard
└── entity_db.json                 # Persistent entity + baseline store
```

---

## Language Support

| Code | Language | Micro Pipeline | Macro Model | Notes |
|---|---|---|---|---|
| EN | English | C++ BPV core | `en_core_web_md` | Full C++ acceleration |
| DE | German | C++ BPV + umlaut/ß normalisation | `de_core_news_md` | ä→ae ö→oe ü→ue ß→ss |
| ES | Spanish | Python BPV + RR×2.0 / LL×1.5 | `es_core_news_md` | Vibrante múltiple override |
| FR | French | Python BPV + silent terminal (S/T/X/D→0) | `fr_core_news_md` | Psychological trail-off model |
| JA | Japanese | Logographic matrix + Keigo formality | `ja_core_news_md` | Kanji/hiragana/katakana ratios + stroke density |

---

## Macro Clusters (all languages)

Each language has 25 seed words per pole (300 total), used to build L2-normalized centroid vectors for cosine similarity scoring.

| Cluster | Primary Pole | Opposing Pole |
|---|---|---|
| Resources | Scarcity | Abundance |
| Power | Control | Submission |
| Visibility | Concealment | Exposure |
| Temporal | Future Projective | Past Nostalgic |
| Cognitive | Scientific | Emotional |
| Kinetic | Aggression | Diplomacy |

---

## Installation

**Requirements:** Python 3.9+, pip

```bash
# 1. Clone and install Python dependencies
pip install fastapi uvicorn spacy numpy

# 2. Install all vector-enabled spaCy models
python -m spacy download en_core_web_md
python -m spacy download de_core_news_md
python -m spacy download es_core_news_md
python -m spacy download fr_core_news_md
python -m spacy download ja_core_news_md
```

> The engine falls back to `_sm` models automatically if an `_md` model is unavailable, and falls back to exact-match scoring if the model has no word vectors.

---

## Building the C++ Core (optional, Windows)

The C++ core accelerates EN and DE analysis. The Python fallback is used automatically if the module is not compiled.

```bash
# Install build tools
pip install cmake ninja

# Build (requires Visual Studio 2022 Build Tools with C++ workload)
cd cpp_core
build_release.bat
```

The compiled `psycho_core.*.pyd` is installed to the project root automatically. Once present, EN and DE micro analysis switches to the C++ backend with no other configuration needed.

---

## Running

```bash
python main.py
```

Open `http://localhost:8000` in a browser.

**Workflow:**
1. Select language
2. *(Optional)* Paste a reference/control text and click **Seed Baselines from Text** to anchor the statistical baseline
3. Paste the intercept text and set an entity designator
4. Click **Run Analysis**
5. Click any window pill (W0, W1 …) to inspect that window's micro/macro fingerprint, Z-scores, and telemetry
6. Toggle **Reader Profile** to switch from authorial signal analysis to target audience profiling
7. Export results via **↓ JSON** or **↓ CSV**

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Run full pipeline on submitted text |
| `POST` | `/api/control` | Seed statistical baselines from a reference text |
| `GET` | `/api/entity` | Fetch current entity record |
| `POST` | `/api/entity` | Create / overwrite entity record |
| `GET` | `/api/entity/ledger` | Retrieve dissonance event ledger |
| `DELETE` | `/api/entity/ledger` | Clear ledger |
| `GET` | `/api/languages` | List supported language codes |
| `GET` | `/api/health` | Liveness check + loaded model list |

**Example request:**
```json
POST /api/analyze
{
  "text": "The strategic withdrawal consolidates resources under centralized authority.",
  "language_code": "EN",
  "window_size": 1000,
  "stride": 500,
  "dissonance_threshold": 2.5
}
```

---

## How the Dissonance Engine Works

For each analysis window the engine:

1. Updates a **Welford online mean/σ** for every micro and macro variable
2. Computes **Z-scores** — how many standard deviations each observation sits from the running baseline
3. Tracks an **EMA** (α = 0.1) for drift visualization
4. Evaluates **11 semantic bridge pairs** that link micro vectors to macro poles (e.g. `intensity ↔ power_control`, `emotion ↔ cognitive_emotional`)
5. Fires a **DissonanceEvent** when |Z_macro − Z_micro| exceeds the configured threshold (default 2.5σ)
6. Classifies the event: *Posturing*, *Suppressed Signal*, or *Psychological Fracture*

Events are persisted to the entity ledger and accumulate a **baseline confidence score** across sessions.
