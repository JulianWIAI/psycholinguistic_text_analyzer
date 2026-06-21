# PsychoLinguistic Analysis Engine v3.8

A real-time psycholinguistic profiling system that detects **steganographic layering**, **subconscious signal patterns**, and **authorial intent divergence** in text. Combines a compiled C++20 orthographic core with spaCy vector-similarity macro analysis and a full Somatic/Archetypal Cipher layer across ten languages spanning Latin, Cyrillic, Abjad RTL, and Hangul Jamo scripts.

---

## Interface

![PsychoLinguistic Analysis Engine — Main Dashboard](docs/screenshot_dashboard.png)
*Main dashboard: language selector (EN/DE/ES/FR/JA/ZH/RU/AR/FA/KO), intercept text input, Steganography Risk chip, Author/Reader profile toggle, Micro-Vector Fingerprint radar (6 subconscious axes), Macro-Cluster Fingerprint radar (6 semantic clusters), Z-score dashboard (6 micro + 12 macro poles), and Raw Telemetry Section A (structural baseline — Total Chars, Total Words, Avg Word Length, Burstiness σ, Lexical Entropy, AI Probability).*

![PsychoLinguistic Analysis Engine — Waveform Charts](docs/screenshot_waveforms.png)
*Four aligned waveform panels sharing a common linear character-position x-axis: Global Waveform Envelope (100 energy buckets, Bézier smooth), Micro Oscilloscope (256 raw letter values, no smoothing), Structural Morse – Punctuation Waveform (neon amber stepped waveform, pause magnitudes 1–4), and Wavelength Telemetry (20-bucket C++ energy envelope per window).*

![PsychoLinguistic Analysis Engine — Somatic Cipher](docs/screenshot_somatic.png)
*Layer 3 Somatic Cipher & Wavelength Physics: complexity tier badge (T3 State/System, avg σ = 5.577), Quersumme archetype (1 — Source: the undivided origin point, pure potential), five-category Archetypal Composition bar (SOV/KIN/RES/LIM/ORI), 5-Axis Archetypal Radar, Complexity Scatter plot (word sum vs. σ, T1/T2/T3 color-coded), and FFT Dominant Harmonics steganographic frequency fingerprint (top 5 bins with magnitude and normalized frequency).*

---

## What It Does

The engine runs every text window through three independent analysis layers and measures the divergence between them:

| Layer | What it measures |
|---|---|
| **Micro (subconscious)** | Orthographic pressure — how letters *look and sound* at a subconscious level, scored via Base Psychological Vectors (BPV) |
| **Macro (conscious)** | Semantic framing — which psychological clusters a text gravitates toward, scored via spaCy cosine similarity |
| **Dissonance Engine** | Statistical divergence (Z-score delta) between the two layers — flags where the author's *conscious framing* contradicts their *subconscious signal* |
| **Somatic Cipher (Layer 3)** | Archetypal frequency analysis — maps every letter to a numeric value and archetypal category, runs an FFT on the resulting waveform to detect hidden rhythmic structures |

A high dissonance delta indicates one of three conditions: **Posturing** (conscious framing exceeds subconscious intensity), **Suppressed Signal** (subconscious leaks past conscious framing), or **Psychological Fracture** (extreme divergence consistent with AI-generated or dissociated text).

---

## Features

- **10-language analysis** — English, German, Spanish, French, Japanese, Chinese, Russian, Arabic, Farsi, Korean
- **C++20 compiled micro-core** — pybind11 BPV engine with `std::jthread` worker pool, zero-copy window sliding; covers Latin (EN/DE), Cyrillic (RU), Abjad RTL (AR/FA), and Hangul Jamo (KO); JA/ZH pass phonetic romanization through C++ for full BPV scoring
- **Universal Tokenization Override (JA/ZH)** — native morpheme/character counts from pykakasi (JA) and jieba (ZH) are used for structural telemetry; phonetic Romaji/Pinyin string passed to C++ BPV so psychological vectors remain on the same A–Z basis as Latin languages
- **Chinese Dual-Signal Stroke-Count Physics Engine** — every Hanzi maps to a stroke count via a 150+ entry lookup table; the ordered `stroke_count_array` is returned per window as a physical ink-density signal; a sudden stroke-density spike signals a switch to complex ideograms
- **C++ `analyze_with_strokes()`** — pybind11 export injects the Python-computed stroke array into `WindowResult.structural_waveform` before serialization
- **C++ compiled somatic core** — modular pybind11 `_somatic_core` with Radix-2 FFT, letter table, and global envelope computation
- **Cyrillic UTF-8 BPV engine** (`analyze_ru`) — 33-bin matrix in full Cyrillic dictionary order (А–Я including Ё); pharyngeal/sibilant interaction coefficients; 5-category archetypal mapping (Origin/Kinetic/Resonant/Liminal/Sovereign); `ru::utf8_next()` shared decoder reused by all non-Latin pipelines
- **Arabic Abjad BPV engine** (`analyze_ar`) — 28-bin matrix in abjadi order; pharyngeal (ع ح) and emphatic (ص ض ط ظ) letters score highest (8–9 BPV); byte stream processed in **logical order** (no RTL reversal — visual rendering is the frontend's responsibility); `dir="rtl"` injected on intercept textareas only, oscilloscope canvases remain LTR
- **Farsi Abjad BPV engine** (`analyze_fa`) — extends Arabic 28-bin core with 4 Farsi-specific letters (پ=28 چ=29 ژ=30 گ=31); same logical-order processing; spaCy `sentencizer` auto-injected when model lacks a parser (e.g. `xx_ent_wiki_sm`)
- **Korean Hangul Jamo BPV engine** (`analyze_ko`) — 24-bin matrix (14 basic consonants + 10 basic vowels); Python `unpack_hangul_to_jamo()` decomposes syllable blocks (U+AC00–U+D7A3) into conjoining Jamo before C++ processing; tense consonants (ㄲ ㄸ ㅃ ㅆ ㅉ) fold to base consonant bin with BPV=9; compound codas fold to primary consonant bin; `total_chars` overridden with native syllable count; whitespace tokenizer override for whole-eojeol macro seed matching
- **Arabic / Korean punctuation in C++ waveform** — `build_punct_waveform()` handles Arabic comma ، (U+060C, D8 8C → magnitude 1) and Arabic question mark ؟ (U+061F, D8 9F → magnitude 4) as 2-byte UTF-8 sequences alongside the standard ASCII and 3-byte en/em-dash punctuation
- **Vector similarity macro scoring** — spaCy `_md` models with cosine similarity against pre-built cluster centroids (25 seed words × 12 poles × 6+ languages); falls back to exact-match on `_sm` models
- **AR/FA macro POS fallback** — when `xx_ent_wiki_sm` returns zero cluster hits (no word vectors), `apply_pos_fallback()` extracts NOUN/VERB/ADJ/PROPN tokens and injects them into the baseline/structural cluster; guarantees a non-empty Driver Matrix on short intercepts; Arabic diacritic stripping, ZWNJ normalization, and 9-prefix clitic expansion registered in the exact-match lookup
- **Z-score bootstrap guard** — `BaselineStats.z_score()` returns the raw value when `n < 2` so the first observation produces a visible signal rather than a silent zero
- **Welford online baseline tracking** — running mean/σ per variable; statistically comparable Z-scores across documents
- **Somatic/Archetypal Cipher** — full A–Z letter-value matrix with 5 archetypal categories, Quersumme (digital root) archetype classification, 3-tier complexity system, and FFT harmonic detection
- **Three aligned waveform charts** — Global Waveform Envelope, Micro Oscilloscope, and Wavelength Telemetry all share the same linear char-position x-axis so features can be compared directly across charts
- **Dynamic Absolute-Length Scaling (Compare Mode)** — in comparison mode every chart's x-axis maximum is derived from `end_char − start_char` of the active window rather than the configured window size
- **Global waveform envelope** — 100-bucket compressed energy signal from the full document; per-window view slices the bucket range to the active window's char range
- **Micro oscilloscope** — up to 256 raw letter-value points, mapped proportionally across the window's full char range
- **Per-window energy envelope (C++)** — `window_envelope` (20 buckets) computed by the C++ somatic core for each analysis window
- **Wavelength Telemetry panels** — one chart per window, each showing its own energy envelope with an x-axis aligned to absolute char positions
- **Σ (Summary) mode** — dedicated overview pill showing the full document in all three waveform charts simultaneously
- **Invisible Unicode Scanner** — C++ `count_hidden_unicode()` and Python `_scan_hidden_unicode()` scan every window for zero-width characters (U+200B/C/D, U+2060, U+FEFF) and trailing whitespace before newlines
- **Punctuation Structural Morse Signal** — `build_punct_waveform()` maps every punctuation mark to a pause magnitude and returns the ordered `punctuation_waveform` array per window; rendered as a neon-amber stepped waveform
- **Linguistic Entropy Engine with Split-Stream Pipeline** — computes burstiness, lexical entropy, and AI probability per window; Split-Stream forks every window into Stream A (raw, for stego/punct/UI) and Stream B (Markdown-stripped, for NLP)
- **Named Entity Targeting** — spaCy NER extracts GPE/ORG/PERSON entities from each window; each entity's containing sentence is scored against all 12 macro poles; top-5 entities returned as `entity_polarity_map`
- **Semantic Snippet Landmarks** — first 3 words of `start_snippet` displayed in Window Span Map and pill hover tooltips
- **Window Span Map** — proportional char-range timeline below the window pills showing exactly which character range each window covers
- **Letter Frequency Panel** — per-window frequency bars; for RU shows А–Я (33 Cyrillic bins), for AR shows 28 abjadi consonants, for FA shows 32 Farsi consonants, for KO shows 24 Jamo bins (decomposed from syllable blocks); compare mode with inline center-anchored micro-bars
- **FFT spectral analysis** — Radix-2 Cooley-Tukey FFT with DC offset removal; returns top 5 harmonic peaks
- **Author / Reader profile toggle** — Reader Profile inverts the Z-score space to model the psychological deficits the target audience brings to the text
- **Raw Telemetry drawer** — structural baseline (chars/words/avg length), BPV character frequency bars, double-letter anomaly chips, full 12-pole driver matrix, steganographic anomaly warning chip, three entropy stat boxes, and Entity Polarity Map
- **Archetypal Legend panel** — fixed floating panel (bottom-right) with 4 tabs: Shape (26-letter 2-column grid with form-to-archetype meanings), Lines (survival metric groupings), Space (spatial orientation groupings), Initials (graphemic iconicity dictionary — all 26 letters with geometric-psychological descriptor and dominant trait); toggled via header button
- **Contextual Help System** — `[?]` icons next to Raw Telemetry, Burstiness σ, Macro Framing, Global Waveform, and Somatic Cipher; hover shows a 1-sentence CSS tooltip; clicking opens a 450px frosted-glass slide-out drawer with 4 beginner-friendly methodology sections and click-to-scroll routing
- **Bulk export** — JSON (full telemetry, all windows) and flat CSV (SPSS/R compatible)
- **Entity ledger** — persistent JSON database tracking baseline drift and dissonance event history across sessions
- **Rolling window tokenizer** — structural boundary detection with configurable window size and stride

---

## Architecture

```
psycholinguistic/
├── main.py                        # FastAPI app entry point
├── api/
│   ├── routes.py                  # REST endpoints + pipeline orchestration
│   │                              # _compute_{letter,cyrillic,arabic,korean}_freq()
│   │                              # RU/AR/FA/KO telemetry override blocks
│   └── compare_routes.py          # Compare-mode endpoints
├── language/
│   ├── router.py                  # Language factory + analyzer cache (10 languages)
│   └── registry.py                # spaCy model registry with _md/_sm fallback
├── micro_layer/
│   ├── base_analyzer.py           # MicroResult + BaseMicroAnalyzer ABC
│   ├── cpp_analyzer.py            # C++ adapter (EN, DE) with Python fallback
│   ├── orthographic_analyzer.py   # Python BPV pipeline (EN baseline)
│   ├── de_analyzer.py             # German: umlaut/ß normalisation → BPV
│   ├── es_analyzer.py             # Spanish: RR×2.0 / LL×1.5 overrides
│   ├── fr_analyzer.py             # French: silent terminal suppression
│   ├── ja_analyzer.py             # Japanese: pykakasi → Hepburn Romaji → C++ BPV
│   ├── zh_analyzer.py             # Chinese: jieba + pypinyin → Pinyin → C++ BPV + stroke array
│   ├── ru_analyzer.py             # Russian: sanitize_ru() + psycho_core.analyze_ru()
│   ├── ar_analyzer.py             # Arabic + Farsi: sanitize_abjad() + analyze_ar()/analyze_fa()
│   ├── ko_analyzer.py             # Korean: unpack_hangul_to_jamo() + psycho_core.analyze_ko()
│   └── somatic_engine.py          # Layer 3: Somatic Cipher, FFT, envelope
├── macro_layer/
│   ├── semantic_analyzer.py       # VectorClusterScorer + SemanticAnalyzer (EN)
│   │                              # apply_pos_fallback() — POS-based injection for
│   │                              # zero-hit intercepts; _surface() for empty-lemma models
│   ├── multilingual_analyzer.py   # Generic multilingual wrapper (auto-sentencizer inject)
│   │                              # AR/FA: diacritic strip, ZWNJ strip, 9-prefix clitic expansion
│   ├── {de,es,fr}_clusters.py     # 25 words × 12 poles per language
│   ├── ja_clusters.py             # JapaneseSemanticAnalyzer + Keigo formality
│   ├── zh_clusters.py             # ChineseSemanticAnalyzer + jieba tokenization
│   ├── ru_clusters.py             # 300 Russian seed words
│   ├── ar_clusters.py             # 300 Arabic seed words
│   ├── fa_clusters.py             # 300 Farsi seed words
│   └── ko_clusters.py             # 300 Korean seed words + KoreanSemanticAnalyzer
│                                  #   (whitespace tokenizer override for whole-eojeol matching)
├── entropy_engine.py              # Burstiness, lexical entropy, AI probability
├── dissonance/
│   └── engine.py                  # Welford stats + Z-scores + EMA + event detection
│                                  # z_score() returns raw value when n < 2 (bootstrap guard)
├── tokenizer/
│   └── rolling_window.py          # Structural boundary tokenizer
├── database/
│   └── schema.py                  # Entity JSON DB helpers
├── cpp_core/                      # C++20 pybind11 BPV module (psycho_core v3.6)
│   ├── include/
│   │   ├── types.h                # WindowResult, MicroVector, MicroScore, WindowResult
│   │   ├── bpv_table.h            # Latin A–Z BPV weights + positional multipliers
│   │   ├── micro_analyzer.h       # Latin OrthographicEngine
│   │   ├── window_engine.h        # Rolling window tokenizer
│   │   ├── pipeline.h             # run_pipeline{,_ru,_ar,_fa,_ko}() declarations
│   │   ├── compare_engine.h
│   │   ├── thread_pool.h
│   │   ├── cyrillic_engine.h      # CyrillicOrthographicEngine (33-bin)
│   │   ├── ru_bpv_table.h         # Cyrillic BPV, archetypes, interaction pairs, utf8_next()
│   │   ├── abjad_engine.h         # AbjadOrthographicEngine (28/32-bin, is_farsi flag)
│   │   ├── ar_bpv_table.h         # Arabic/Farsi BPV, archetypes, interaction pairs
│   │   ├── ko_engine.h            # KoreanOrthographicEngine (24-bin Jamo)
│   │   └── ko_bpv_table.h         # Jamo BPV, ONSET/NUCLEUS/CODA dispatch tables, jamo_lookup()
│   ├── src/
│   │   ├── micro_analyzer.cpp     # Latin five-rule BPV pipeline
│   │   ├── window_engine.cpp      # Rolling window tokenizer
│   │   ├── pipeline.cpp           # run_pipeline{,_ru,_ar,_fa,_ko}() + punct/stego helpers
│   │   ├── compare_engine.cpp     # Side-by-side dual-document analysis
│   │   ├── cyrillic_analyzer.cpp  # Cyrillic five-rule pipeline
│   │   ├── abjad_analyzer.cpp     # Abjad five-rule pipeline (logical order, diacritic skip)
│   │   ├── ko_analyzer.cpp        # Jamo five-rule pipeline ({bin,bpv} dual word buffer)
│   │   ├── thread_pool.cpp        # C++20 std::jthread worker pool
│   │   └── bindings.cpp           # pybind11 exports: analyze{,_ru,_ar,_fa,_ko,_with_strokes}()
│   ├── CMakeLists.txt
│   ├── setup.py
│   └── build_release.bat
├── cpp/                           # C++17 pybind11 Somatic Core (_somatic_core)
│   ├── letter_table.h / .cpp
│   ├── fft.h / .cpp
│   ├── somatic_analyzer.h / .cpp
│   ├── bindings.cpp
│   ├── CMakeLists.txt
│   ├── setup.py
│   └── build.sh
├── templates/
│   └── index.html                 # Single-page dashboard (Chart.js, vanilla JS)
│                                  # ALPHABET.{LATIN,CYRILLIC,ARABIC,FARSI,HANGUL}
│                                  # dir="rtl" injection for AR/FA textareas
│                                  # Archetypal Legend panel (Shape/Lines/Space tabs)
│                                  # Contextual Help drawer (4 methodology sections)
└── entity_db.json                 # Persistent entity + baseline store
```

---

## Dashboard Panels

### Window Selection & Span Map

Below the run controls, a row of **window pills** (W0, W1, W2 …) lets you jump between analysis windows. Hovering any pill shows a tooltip with the character/line range, the 3-word **semantic snippet landmark** (`"The strategic withdrawal…"`), and the reset reason. Beneath the pills, a **Window Span Map** renders a proportional bar for each window; below each bar a sub-line displays the snippet landmark and exact character range. Clicking any bar or pill selects that window and updates all charts.

The special **Σ pill** activates summary mode — all three waveform charts switch to full-document view and all analysis cards are shown together for a quick overview.

### Three Aligned Waveform Charts

All three charts share a **linear character-position x-axis** with identical bounds for the active window:

| Chart | Data source | Resolution | Rendering |
|---|---|---|---|
| **Global Waveform Envelope** | `global_waveform_envelope` (100 buckets, full document) sliced to active window's char range | 100 buckets total | Bezier smooth, filled |
| **Micro Oscilloscope** | `micro_wavelength` (up to 256 raw letter values per window) | Up to 256 points | Sharp line, no smoothing |
| **Wavelength Telemetry** | `window_envelope` (20-bucket C++ envelope for this window) | 20 buckets | Bezier smooth, filled |

### Letter Frequency Panel

Shows the per-window letter distribution. The alphabet displayed depends on language:

| Language | Alphabet | Bins |
|---|---|---|
| EN / DE / ES / FR | A–Z (Latin) | 26 |
| JA / ZH | A–Z (Romaji / Pinyin phonetic proxy) | 26 |
| RU | А–Я (Cyrillic, dictionary order, incl. Ё) | 33 |
| AR | ا–ي (Arabic abjadi order) | 28 |
| FA | ا–گ (Arabic 28 + پ چ ژ گ) | 32 |
| KO | ㄱ–ㅣ (14 consonants + 10 vowels, decomposed from syllables) | 24 |

In compare mode, each row displays **inline micro-bars**: semi-transparent cyan (Text A, right-to-left) and crimson (Text B, left-to-right) fills centered on each letter.

### RTL Languages (AR / FA)

When Arabic or Farsi is selected, `dir="rtl"` is injected on the intercept textarea(s) so text flows right-to-left as typed. The Micro Oscilloscope and all other `<canvas>`-based waveform charts are unaffected — they always maintain a strictly LTR time-series x-axis regardless of text direction.

### Chinese Script Panel (ZH)

When the active window is Chinese, a dedicated **ZH script panel** shows Hanzi count, average stroke count, max strokes, and complexity index. Below it, the **Dual-Signal Stroke-Count Oscilloscope** renders `stroke_count_array` in neon gold.

### Archetypal Legend Panel

A fixed floating panel (bottom-right, toggled via the **⊕ Legend** header button) with a dark amber theme and four tabs:

| Tab | Content |
|---|---|
| **Shape** | 26-letter grid mapping each letterform's geometry to its somatic archetype and associated concepts |
| **Lines** | Groups letters by line count (1-line abstract, 2-line structural, 3-line systematic, 4-line material) |
| **Space** | Groups letters by spatial orientation (vertical axis, horizontal, diagonal, enclosed, open arc) |
| **Initials** | Graphemic iconicity dictionary — all 26 letters with geometric label (e.g. "Kinetic Strike", "Open Vessel") and dominant psychological trait; cross-reference for the Lexical Affinity Radar cluster assignments |

### Contextual Help System

`[?]` icons (grey-blue, brightening on hover with a 1-sentence CSS tooltip) appear next to five major dashboard headers:

| Icon location | Links to drawer section |
|---|---|
| Raw Telemetry & Attribution | Raw Telemetry & Structural Baseline |
| Burstiness σ | Raw Telemetry & Structural Baseline |
| Macro — Conscious Framing · 6-Cluster | Dissonance Radars |
| Global Waveform Envelope | The Waveform Physics |
| Somatic Cipher & Wavelength Physics | Layer 3 · Somatic Cipher & FFT |

Clicking any icon (or the **? Methodology / Docs** sidebar button) opens a 450 px frosted-glass slide-out drawer from the right edge with four beginner-friendly sections. Each section explains concepts, defines key terms, and contextualizes the output for non-specialist readers without removing any analytical depth from the interface.

---

## Layer 3: Somatic / Archetypal Cipher

### Letter Value Matrix

Each letter maps to an exact numeric value and an **archetypal category**:

| Letter | Value | Category | | Letter | Value | Category |
|--------|-------|----------|-|--------|-------|----------|
| A | 1 | Origin | | N | 14 | Liminal |
| B | 2 | Kinetic | | O | 15 | Resonant |
| C | 3 | Resonant | | P | 16 | Kinetic |
| D | 4 | Sovereign | | Q | 17 | Sovereign |
| E | 5 | Kinetic | | R | 18 | Liminal |
| F | 6 | Kinetic | | S | 19 | Kinetic |
| G | 7 | Liminal | | T | 20 | Sovereign |
| H | 8 | Resonant | | U | 21 | Resonant |
| I | 9 | Sovereign | | V | 22 | Kinetic |
| J | 10 | Kinetic | | W | 23 | Sovereign |
| K | 11 | Sovereign | | X | 24 | Sovereign |
| L | 12 | Resonant | | Y | 25 | Resonant |
| M | 13 | Resonant | | Z | 26 | Sovereign |

German umlauts receive intermediate values: **Ä = 1.5** (Liminal), **Ö = 15.5** (Liminal), **Ü = 21.5** (Liminal).

### Quersumme (Digital Root) Archetypes

| QS | Archetype |
|----|-----------|
| 1 | Source |
| 2 | Bond |
| 3 | Overflow |
| 4 | Foundation |
| 5 | Friction |
| 6 | Grounding |
| 7 | Precursor |
| 8 | Infinity / State |
| 9 | Transcendent |

### Complexity Tiers

| Tier | σ Range | Label |
|------|---------|-------|
| T1 | σ < 2.0 | Somatic / Universal |
| T2 | 2.0 ≤ σ < 5.0 | Archetypal Bridge |
| T3 | σ ≥ 5.0 | State / System |

### FFT Spectral Analysis

Before running the FFT on the 256-letter micro array, the engine subtracts the **mean of the real (non-padded) samples** from every value, eliminating the DC offset. The Radix-2 Cooley-Tukey FFT returns the **top 5 harmonic peaks** (bin index, magnitude, normalized frequency) from bins 1 through N/2−1.

---

## Language Support

| Code | Language | Script | Micro Pipeline | Macro Model | Notes |
|---|---|---|---|---|---|
| EN | English | Latin | C++ BPV core (26-bin) | `en_core_web_md` | Full C++ acceleration |
| DE | German | Latin | C++ BPV + umlaut/ß normalisation | `de_core_news_md` | ä→ae ö→oe ü→ue ß→ss; Ä/Ö/Ü scored separately in somatic |
| ES | Spanish | Latin | Python BPV + RR×2.0 / LL×1.5 | `es_core_news_md` | Vibrante múltiple override |
| FR | French | Latin | Python BPV + silent terminal (S/T/X/D→0) | `fr_core_news_md` | Psychological trail-off model |
| JA | Japanese | Logographic | pykakasi → Hepburn Romaji → C++ BPV | `ja_core_news_md` | Script ratios + stroke density + Keigo formality layer |
| ZH | Chinese | Logographic | jieba → pypinyin → Pinyin → C++ BPV + Hanzi stroke array | `zh_core_web_md` | Dual-Signal Engine; `analyze_with_strokes()` |
| RU | Russian | Cyrillic | `sanitize_ru()` + C++ `analyze_ru()` (33-bin UTF-8) | `ru_core_news_md` | 33 Cyrillic bins А–Я; pharyngeal/sibilant interaction pairs |
| AR | Arabic | Abjad RTL | `sanitize_abjad()` + C++ `analyze_ar()` (28-bin UTF-8, logical order) | `xx_ent_wiki_sm` | Pharyngeal/emphatic BPV 8–9; dir=rtl on UI textareas; sentencizer auto-injected; POS fallback + diacritic/clitic normalization for macro |
| FA | Farsi | Abjad RTL | `sanitize_abjad()` + C++ `analyze_fa()` (32-bin UTF-8, logical order) | `xx_ent_wiki_sm` | Extends AR with پ(28) چ(29) ژ(30) گ(31); ZWNJ compound-word normalization |
| KO | Korean | Hangul | `unpack_hangul_to_jamo()` + C++ `analyze_ko()` (24-bin Jamo) | `ko_core_news_sm` | Syllable blocks decomposed to conjoining Jamo; tense consonants fold to base bin with BPV=9; whitespace tokenizer for whole-eojeol macro matching |

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
pip install -r requirements.txt

# 2. Install spaCy models
# Latin languages
python -m spacy download en_core_web_md
python -m spacy download de_core_news_md
python -m spacy download es_core_news_md
python -m spacy download fr_core_news_md
# Logographic
python -m spacy download ja_core_news_md
python -m spacy download zh_core_web_md
# Cyrillic
python -m spacy download ru_core_news_md
# Abjad RTL (shared model for AR + FA)
python -m spacy download xx_ent_wiki_sm
# Hangul
python -m spacy download ko_core_news_sm
```

`requirements.txt` includes: `fastapi`, `uvicorn`, `spacy`, `numpy>=1.24.0`, `pybind11>=2.11.0`, `pykakasi>=2.2.1`, `jieba>=0.42.1`, `pypinyin>=0.49.0`.

> The engine falls back to `_sm` models automatically if an `_md` model is unavailable, and falls back to exact-match scoring if the model has no word vectors. The Python somatic fallback (numpy FFT) is used automatically if `_somatic_core` is not compiled.

---

## Building the C++ BPV Core (`psycho_core`)

The BPV core provides compiled pipelines for all non-logographic languages and the `analyze_with_strokes()` passthrough for JA/ZH. The Python fallback is used automatically if not compiled.

### macOS / Linux

```bash
pip install pybind11

cd cpp_core
MACOSX_DEPLOYMENT_TARGET=11.0 python setup.py build_ext --inplace
```

> **macOS note:** `MACOSX_DEPLOYMENT_TARGET=11.0` is required for `std::jthread` / `std::stop_token` (C++20, macOS 11.0+).

Alternatively, build with CMake:

```bash
cd cpp_core
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j
cmake --install build --prefix ..
```

### Windows

Requires Visual Studio 2022 Build Tools with the C++ workload and CMake + Ninja.

```bat
cd cpp_core
build_release.bat
```

### C++ BPV module structure (`psycho_core` v3.6)

| File | Responsibility |
|---|---|
| `src/pipeline.cpp` | All five `run_pipeline*()` variants; `count_hidden_unicode()`; `build_punct_waveform()` (2-byte Arabic + 3-byte en/em-dash + ASCII) |
| `src/micro_analyzer.cpp` | Latin A–Z five-rule BPV pipeline |
| `src/cyrillic_analyzer.cpp` | Cyrillic 33-bin five-rule BPV pipeline; reuses `ru::utf8_next()` |
| `src/abjad_analyzer.cpp` | Abjad 28/32-bin five-rule BPV pipeline; logical order; diacritics skipped without word flush |
| `src/ko_analyzer.cpp` | Hangul Jamo 24-bin five-rule BPV pipeline; `{bin,bpv}` dual word buffer for tense consonant BPV override |
| `src/compare_engine.cpp` | Side-by-side dual-document analysis for Compare Mode |
| `src/window_engine.cpp` | Rolling window tokenizer with structural boundary detection |
| `src/thread_pool.cpp` | C++20 `std::jthread` worker pool with `stop_token` RAII shutdown |
| `src/bindings.cpp` | pybind11 exports: `analyze()`, `analyze_ru()`, `analyze_ar()`, `analyze_fa()`, `analyze_ko()`, `analyze_with_strokes()`, `analyze_sections_parallel()`, `compare_texts()` |
| `include/ru_bpv_table.h` | Cyrillic BPV, archetypes, interaction pairs, visual anchors; `ru::utf8_next()` (shared by all UTF-8 engines) |
| `include/ar_bpv_table.h` | Arabic/Farsi BPV, abjadi ordering, 36-slot codepoint dispatch table, `arabic_index()` |
| `include/ko_bpv_table.h` | Jamo BPV, ONSET[19] / NUCLEUS[21] / CODA[27] dispatch tables, `jamo_lookup()`, compat Jamo mapping |

---

## Building the C++ Somatic Core (`_somatic_core`)

```bash
pip install cmake pybind11

cd cpp
bash build.sh        # Unix/macOS
# or
cd cpp && pip install .
```

| File | Responsibility |
|---|---|
| `letter_table.cpp` | Compile-time A–Z value/category lookup; 2-byte UTF-8 umlaut handler |
| `fft.cpp` | Radix-2 Cooley-Tukey FFT; `dominant_harmonics()` with DC offset removal |
| `somatic_analyzer.cpp` | UTF-8 tokenizer; word scoring; 256-point micro waveform; 100-bucket global envelope; per-window envelope |
| `bindings.cpp` | pybind11 exports: `analyze(text)`, `compute_global_envelope(text, n_buckets)` |

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
5. Click any window pill (W0, W1 …) to inspect that window's micro/macro fingerprint, Z-scores, somatic cipher, and all three aligned waveform charts
6. Click the **Σ pill** for a full-document summary
7. Use the **Window Span Map** below the pills to see at a glance which character range each window covers
8. Toggle **Reader Profile** to switch from authorial signal analysis to target audience profiling
9. Export results via **↓ JSON** or **↓ CSV**
10. Click **⊕ Legend** (header) to open the Archetypal Letter Legend panel
11. Click **? Methodology / Docs** (sidebar) or any `[?]` icon to open the contextual help drawer

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

**Top-level response fields:**

```json
{
  "document_id": "doc_a3f9b1",
  "language": "EN",
  "total_windows": 3,
  "global_waveform_envelope": [8.2, 11.4, 9.7, ...],
  "windows": [...]
}
```

**Per-window raw telemetry fields** (`windows[n].raw_telemetry`):

```json
{
  "total_chars": 847,
  "total_words": 142,
  "avg_word_length": 5.96,
  "top_micro_chars": {"E": 91, "T": 72, "А": 68},
  "double_letter_anomalies": {"LL": 3, "SS": 2},
  "macro_drivers": {"resources_scarcity": {"lack": 1.4}},
  "letter_frequencies": {"A": 68, "B": 12, ...},
  "stroke_count_array": [8, 13, 4, 11],
  "hidden_unicode_count": 0,
  "stego_anomaly_flag": false,
  "punctuation_waveform": [1, 2, 1, 4, 2, 3],
  "sentence_count": 8,
  "burstiness": 6.42,
  "lexical_entropy": 0.71,
  "ai_probability_score": 0.18
}
```

`letter_frequencies` — full frequency dict for the window. Alphabet depends on language (A–Z for Latin/JA/ZH, А–Я for RU, abjadi for AR/FA, 24 Jamo for KO).

`stroke_count_array` — ZH only. Ordered list of stroke counts per Hanzi.

`hidden_unicode_count` / `stego_anomaly_flag` — zero-width Unicode characters and trailing whitespace before newlines.

`punctuation_waveform` — pause magnitudes per punctuation mark (`,`=1, `.`/`:`/`-`=2, `;`/em-dash=3, `!`/`?`/`؟`=4, `،`=1).

`burstiness` — population σ of per-sentence word counts. Human ≈ 6–12; AI ≈ 0–3.

`lexical_entropy` — unique lemmas / total lemmas.

`ai_probability_score` — composite 0.0–1.0: `burst_ai × 0.65 + entropy_ai × 0.35`.

**Per-window macro fields** (`windows[n].macro`):

```json
{
  "cluster_scores": {
    "power": {"control": 0.042, "submission": 0.011}
  },
  "total_words": 142,
  "entity_polarity_map": [
    {"entity": "NATO",   "label": "ORG",    "driver": "power/control",       "weight": 0.88},
    {"entity": "Berlin", "label": "GPE",    "driver": "temporal/past_nostalgic", "weight": 0.76}
  ]
}
```

---

## How the Dissonance Engine Works

For each analysis window the engine:

1. Updates a **Welford online mean/σ** for every micro and macro variable
2. Computes **Z-scores** — how many standard deviations each observation sits from the running baseline; returns the raw value on the first observation (n < 2) so bootstrap windows are never silently zeroed
3. Tracks an **EMA** (α = 0.1) for drift visualization
4. Evaluates **11 semantic bridge pairs** linking micro vectors to macro poles
5. Fires a **DissonanceEvent** when |Z_macro − Z_micro| exceeds the configured threshold (default 2.5σ)
6. Classifies the event: *Posturing*, *Suppressed Signal*, or *Psychological Fracture*

Events are persisted to the entity ledger and accumulate a **baseline confidence score** across sessions.

---

## Changelog

### v3.8
- **Legend panel — Initials tab (4th tab)** — graphemic iconicity dictionary for all 26 Latin letters in the same `.leg-shape-grid` two-column format as the Shape tab; each entry has a geometric label (e.g. "Kinetic Strike", "Open Vessel") and italic dominant trait; serves as a visual cross-reference for the Lexical Affinity Radar cluster assignments; `legendTab(3)` handled automatically by the existing generic tab switcher with no JS changes

### v3.7
- **Contextual Help System** — `[?]` icons (grey-blue, CSS tooltip on hover) injected next to Raw Telemetry, Burstiness σ, Macro Conscious Framing, Global Waveform Envelope, and Somatic Cipher; click-to-scroll routing to the correct drawer section; `openHelp(sectionId)` / `closeHelp()` JS
- **Methodology slide-out drawer** — 450 px frosted-glass panel (`backdrop-filter:blur(10px)`, `rgba(14,17,26,.96)`) with `.3s cubic-bezier` open/close animation and neon-accented scrollbar; z-index 10000 (above Legend panel); four beginner-friendly sections: Raw Telemetry & Structural Baseline, Dissonance Radars, The Waveform Physics, Layer 3 Somatic Cipher & FFT
- **? Methodology / Docs** button added to left sidebar panel
- **Archetypal Legend floating panel** — fixed bottom-right panel (332×430 px, dark amber theme) with three tabs: Shape (26-letter form-to-archetype grid), Lines (line-count survival groupings), Space (spatial orientation groupings); toggled via **⊕ Legend** header button

### v3.6
- **Korean (KO) Hangul Jamo support** — C++ `analyze_ko()` pipeline with 24-bin matrix (14 basic consonants ㄱ–ㅎ + 10 basic vowels ㅏ–ㅣ); `ko_bpv_table.h` with ONSET[19] / NUCLEUS[21] / CODA[27] conjoining Jamo dispatch tables and `jamo_lookup()`; tense consonants (ㄲ ㄸ ㅃ ㅆ ㅉ) fold to base bin with BPV=9; compound codas fold to primary consonant bin; 5-category archetypal mapping (Origin/Kinetic/Resonant/Liminal/Sovereign); 7 interaction pairs
- **Python Jamo decomposition bridge** — `unpack_hangul_to_jamo()` in `micro_layer/ko_analyzer.py` decomposes syllable blocks U+AC00–U+D7A3 into conjoining Onset/Nucleus/Coda Jamo via standard Unicode offset formula; `sanitize_ko()` Stream B pre-processor; `KoreanOrthographicAnalyzer` overrides `total_chars` with native syllable count (not inflated Jamo count)
- **Korean macro layer** — `KoreanSemanticAnalyzer` in `macro_layer/ko_clusters.py` with 300 Korean seed words; spaCy whitespace tokenizer override for whole-eojeol seed matching (avoids MeCab-Ko morpheme fragmentation); sentencizer auto-injected when model lacks a parser
- **Korean letter frequency** — `_compute_korean_freq()` in `routes.py` decomposes each syllable block and maps Onset/Nucleus/Coda to 24 Jamo bins; `ALPHABET.HANGUL` (24 glyphs) + Hangul decomposition branch in `computeLetterFreq()` JS; 🇰🇷 KO button with `--ko: #f06890` theme
- **AR/FA macro flatline fix** — `apply_pos_fallback()` in `semantic_analyzer.py` fires when zero cluster hits are returned; injects NOUN/VERB/ADJ/PROPN tokens into `baseline/structural`; `_surface()` helper uses `(token.lemma_ or token.text).lower()` to handle `xx_ent_wiki_sm`'s empty-lemma behavior; Arabic diacritic stripping (U+064B–U+065F), Farsi ZWNJ stripping (U+200C), and 9 clitic prefix variants registered in `_build_lookup()`
- **Z-score bootstrap guard** — `BaselineStats.z_score()` returns raw `value` when `n < 2` so first-window Z-scores are never silently zeroed

### v3.5
- **Arabic (AR) and Farsi (FA) Abjad RTL support** — C++ `analyze_ar()` (28-bin) and `analyze_fa()` (32-bin) pipelines; `ar_bpv_table.h` with 36-slot codepoint dispatch table and `arabic_index()` mapping U+0627–U+064A; Farsi-specific letters پ(28) چ(29) ژ(30) گ(31) handled as early special cases; pharyngeal/emphatic letters score 8–9 BPV; byte stream processed in logical order — no RTL reversal in C++
- **Abjad Stream B pre-processor** — `sanitize_abjad()` in `micro_layer/ar_analyzer.py`: 9-step pipeline strips diacritics (U+064B–U+065F, tatweel U+0640), Markdown, Latin tokens, and injects periods for sentence segmentation; diacritics skipped without word flush in C++ so لِكتاب and لكتاب score identically
- **Arabic punctuation in C++ waveform** — `build_punct_waveform()` extended with 2-byte checks for ، (U+060C → magnitude 1) and ؟ (U+061F → magnitude 4) before the 3-byte en/em-dash checks
- **RTL UI directionality** — `selectLang()` injects `dir="rtl"` on intercept textareas when AR or FA is active; all `<canvas>` waveform charts are unaffected and maintain strict LTR time-series ordering
- **sentencizer auto-inject** — `MultilingualSemanticAnalyzer.__init__()` checks for `parser`/`senter`/`sentencizer` presence and injects `sentencizer` when none exists, fixing `[E030] Sentence boundaries unset` on `xx_ent_wiki_sm`
- **AR/FA letter frequency** — `_compute_arabic_freq()` with Alef variant folding (آ أ إ → ا); `ALPHABET.ARABIC` (28 bins) and `ALPHABET.FARSI` (32 bins) in frontend; Alef/Ya/Waw variant folding in `computeLetterFreq()` JS

### v3.4
- **Russian (RU) Cyrillic support** — C++ `analyze_ru()` pipeline with 33-bin matrix in full dictionary order (А–Я including Ё); `ru_bpv_table.h` with BPV weights, archetypal categories, visual complexity anchors (Ж Ш Щ Ы Ю), double-letter Gm multipliers, and 7 canonical interaction pairs; `ru::utf8_next()` shared UTF-8 decoder reused by all subsequent non-Latin engines
- **Cyrillic Stream B pre-processor** — `sanitize_ru()` in `micro_layer/ru_analyzer.py`: strips fenced code blocks, inline code, horizontal rules, Markdown prefixes, and Latin tokens before the Cyrillic payload reaches C++ BPV and spaCy
- **RU telemetry override** — `routes.py` replaces Latin-regex counts with C++ Cyrillic output (`total_chars`, `total_words`, `avg_word_length`, `top_micro_chars`, `double_letter_anomalies`) for RU windows
- **Cyrillic letter frequency** — `_compute_cyrillic_freq()` in `routes.py`; `ALPHABET.CYRILLIC` (33 bins) in frontend

### v3.3
- **Invisible Unicode Scanner** — C++ `count_hidden_unicode()` and Python `_scan_hidden_unicode()` scan for zero-width characters (U+200B/C/D, U+2060, U+FEFF) and trailing whitespace before newlines; UI shows red `⚠ STEGANOGRAPHIC ANOMALY` chip
- **Punctuation Structural Morse Signal** — `build_punct_waveform()` returns ordered pause-magnitude array; neon-amber stepped waveform in Somatic Panel D; compare mode dual-dataset overlay
- **Linguistic Entropy Engine + Split-Stream Pipeline** — `entropy_engine.py` computes burstiness, lexical entropy, and AI probability; Split-Stream forks each window into Stream A (raw) and Stream B (Markdown-stripped) before NLP
- **Named Entity Targeting** — `extract_entity_polarity()` scores each GPE/ORG/PERSON entity's containing sentence against all 12 macro poles; top-5 returned as `entity_polarity_map`; rendered in telemetry drawer Section D
- **Semantic Snippet Landmarks** — first 3 words of `start_snippet` displayed in Window Span Map sub-lines and pill hover tooltips

### v3.2
- **Chinese (ZH) language support** — jieba tokenization, pypinyin Pinyin romanization, C++ BPV scoring, `zh_core_web_md` macro analysis, Hanzi stroke-count array, ZH script panel in UI
- **Dual-Signal Stroke-Count Physics Engine** — `stroke_count_array` (one int per Hanzi) from 150+ entry lookup table; drives neon-gold oscilloscope in UI
- **C++ `analyze_with_strokes()`** — injects Python-computed stroke array into `WindowResult.structural_waveform`
- **Dynamic Absolute-Length Scaling (Compare Mode)** — x-axis maximum derived from `end_char − start_char`; each dataset independently scaled

### v3.1
- **Unified x-axis** — Global Waveform Envelope, Micro Oscilloscope, and Wavelength Telemetry share identical `type: 'linear'` bounds per window
- **Micro Oscilloscope proportional mapping** — letter values mapped proportionally across the full `start_char → end_char` range
- **Per-window energy envelope from C++** — `window_envelope` (20 buckets) added to API response per window
- **Wavelength Telemetry `TelwModule`** — refactored into `_telwBuildWindowPanels`, `_telwBuildFullDocChart`, `_telwShowActivePanel`

### v3.0
- **Wavelength Telemetry per-window panels** — one Chart.js line chart per analysis window with linear x-axis
- **Window Span Map** — proportional bar chart below window pills; clickable to navigate
- **Σ (Summary) mode** — overview pill with all analysis cards aggregated across the full document

### v2.1
- C++ core (`psycho_core`) with pipeline, compare engine, and `std::jthread` thread pool
- Vector similarity macro scoring with spaCy `_md` models
- German language support with umlaut BPV normalisation
- Raw telemetry drawer (structural, frequency, driver matrix)
- Global waveform envelope and micro oscilloscope
