"""
MODULE 6 — FastAPI Routes (Backend)
Exposes the full multi-language analysis pipeline as REST API endpoints.

All endpoints now accept an optional language_code parameter:
    "EN" (default) | "ES" | "FR" | "JA"

The LanguageRouter selects the correct micro + macro analyzers; the
dissonance engine always receives the standardized six-vector MicroResult
so Z-scores and baselines remain cross-language comparable.

Endpoints:
    POST   /api/analyze         — full pipeline on submitted text
    POST   /api/control         — seed baselines from a control text
    GET    /api/entity          — fetch current entity record
    POST   /api/entity          — create / overwrite entity record
    GET    /api/entity/ledger   — dissonance event ledger
    DELETE /api/entity/ledger   — clear ledger
    GET    /api/languages       — list supported language codes
    GET    /api/health          — liveness check
"""

import re
import uuid
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import database.schema as db
from dissonance.engine import DissonanceEngine
from entropy_engine import compute_entropy_metrics, sanitize_for_entropy
from language.router import LanguageRouter, SUPPORTED_LANGUAGES
from micro_layer.somatic_engine import SomaticEngine
from tokenizer.rolling_window import RollingWindowTokenizer

router = APIRouter()

DB_PATH = "entity_db.json"

# ---------------------------------------------------------------------------
# Singletons — shared across requests for baseline continuity
# ---------------------------------------------------------------------------
_lang_router       = LanguageRouter()
_dissonance_engine = DissonanceEngine()
_somatic_engine    = SomaticEngine()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw text to analyze")
    language_code: str = Field("EN", description="ISO language code: EN, DE, ES, FR, JA, ZH")
    document_id: Optional[str] = Field(None, description="Optional document identifier")
    window_size: int = Field(1000, ge=100, description="Characters per window")
    stride: int = Field(500, ge=50, description="Step size between windows")
    dissonance_threshold: float = Field(2.5, ge=0.5, description="Δ threshold for events")


class ControlTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Control / reference text")
    language_code: str = Field("EN", description="ISO language code: EN, DE, ES, FR, JA, ZH")


class EntityCreateRequest(BaseModel):
    primary_designator: str
    known_aliases: List[str] = []
    suspected_agency: str = "Unknown"
    steganography_risk: str = "High"


# ---------------------------------------------------------------------------
# Core pipeline helper
# ---------------------------------------------------------------------------

_WORD_RE   = re.compile(r"[A-Za-z]+")
_LETTER_RE = re.compile(r"[A-Za-z]")

# Zero-width / invisible Unicode byte sequences (UTF-8 encoded)
_HIDDEN_SEQS = [
    b"\xe2\x80\x8b",  # U+200B Zero-Width Space
    b"\xe2\x80\x8c",  # U+200C Zero-Width Non-Joiner
    b"\xe2\x80\x8d",  # U+200D Zero-Width Joiner
    b"\xe2\x81\xa0",  # U+2060 Word Joiner
    b"\xef\xbb\xbf",  # U+FEFF BOM
]
# Punctuation magnitude table
_PUNCT_MAP: Dict[str, int] = {",": 1, ".": 2, ":": 2, "-": 2, ";": 3, "!": 4, "?": 4}
_PUNCT_UTF8: Dict[bytes, int] = {
    b"\xe2\x80\x93": 2,  # U+2013 en dash
    b"\xe2\x80\x94": 3,  # U+2014 em dash
}


def _compute_letter_freq(text: str) -> Dict[str, int]:
    """Return a full A-Z frequency dict for *text* (uppercase keys, all 26 present)."""
    freq: Dict[str, int] = {chr(i): 0 for i in range(65, 91)}
    for ch in text.upper():
        if "A" <= ch <= "Z":
            freq[ch] += 1
    return freq


def _scan_hidden_unicode(text: str) -> Dict[str, Any]:
    """
    Scan *text* (original window text, any language) for steganographic Unicode.
    Returns hidden_unicode_count and stego_anomaly_flag.
    Runs on the native text for all languages — catches ZW chars embedded in
    Japanese/Chinese text that the C++ phonetic path would not see.
    """
    raw = text.encode("utf-8", errors="replace")
    count = 0
    for seq in _HIDDEN_SEQS:
        count += raw.count(seq)
    # Trailing whitespace before newline (binary pacing)
    for line in text.split("\n"):
        stripped = line.rstrip(" \t")
        count += len(line) - len(stripped)
    return {"hidden_unicode_count": count, "stego_anomaly_flag": count > 0}


def _build_punct_waveform(text: str) -> List[int]:
    """
    Return an ordered array of pause-magnitude values for each punctuation mark
    in *text*.  Runs on the original text so native punctuation is captured for
    all languages.
    """
    wave: List[int] = []
    raw = text.encode("utf-8", errors="replace")
    i = 0
    n = len(raw)
    while i < n:
        # Check 3-byte sequences first
        if i + 2 < n:
            tri = bytes(raw[i:i+3])
            if tri in _PUNCT_UTF8:
                wave.append(_PUNCT_UTF8[tri])
                i += 3
                continue
        ch = chr(raw[i]) if raw[i] < 128 else ""
        if ch in _PUNCT_MAP:
            wave.append(_PUNCT_MAP[ch])
        i += 1
    return wave


# ---------------------------------------------------------------------------
# Localization helpers — line numbers and text snippets from char offsets
# ---------------------------------------------------------------------------

def _char_to_line(text: str, char_offset: int) -> int:
    """Return the 1-based line number for *char_offset* inside *text*."""
    return text[:char_offset].count("\n") + 1


def _extract_snippets(text: str, start: int, end: int, max_chars: int = 60):
    """
    Return (start_snippet, end_snippet) for the window at [start, end).

    Each snippet is at most *max_chars* characters, trimmed to a word boundary
    so words are never cut in the middle.
    """
    window = text[start:end]

    # Start snippet: first max_chars chars trimmed to last full word
    raw_start = window.lstrip()[:max_chars]
    if len(window.lstrip()) > max_chars:
        last_space = raw_start.rfind(" ")
        if last_space > 0:
            raw_start = raw_start[:last_space]
    start_snippet = raw_start.strip()

    # End snippet: last max_chars chars trimmed to first full word from cut
    raw_end = window.rstrip()
    if len(raw_end) > max_chars:
        raw_end = raw_end[-max_chars:]
        first_space = raw_end.find(" ")
        if first_space >= 0:
            raw_end = raw_end[first_space + 1:]
    end_snippet = raw_end.strip()

    return start_snippet, end_snippet


def _compute_window_telemetry(win_text: str, macro_hits: list) -> Dict[str, Any]:
    """
    Build raw telemetry for one analysis window.
    Sections:
      structural   — total_chars, total_words, avg_word_length
      micro_freq   — top_micro_chars (top-5 letters by raw count)
      double_anom  — double_letter_anomalies (XX → count)
      macro_drivers— {cluster_pole: {lemma: weight}} top-5 per pole
    """
    words = _WORD_RE.findall(win_text)
    total_words = len(words)
    all_chars   = "".join(w.upper() for w in words)
    total_chars = len(all_chars)

    # Top-5 characters by raw frequency
    top_micro_chars: Dict[str, int] = dict(Counter(all_chars).most_common(5))

    # Double-letter anomalies (XX pairs, same algorithm as C++ pass A)
    dl_counts: Dict[str, int] = {}
    for word in words:
        w = word.upper()
        i = 0
        while i < len(w) - 1:
            if w[i] == w[i + 1]:
                pair = w[i] * 2
                dl_counts[pair] = dl_counts.get(pair, 0) + 1
                i += 2
            else:
                i += 1

    # Macro drivers: aggregate hit weights per (cluster_pole) → lemma
    grouped: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for hit in macro_hits:
        grouped[f"{hit.cluster}_{hit.pole}"][hit.lemma] += hit.weight

    macro_drivers: Dict[str, Dict[str, float]] = {
        pole_key: dict(
            sorted(lemmas.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        for pole_key, lemmas in grouped.items()
    }

    return {
        "total_chars":             total_chars,
        "total_words":             total_words,
        "avg_word_length":         round(total_chars / max(1, total_words), 2),
        "top_micro_chars":         top_micro_chars,
        "double_letter_anomalies": dl_counts,
        "macro_drivers":           macro_drivers,
    }


def _flatten_macro(cluster_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Flatten {cluster: {pole: score}} → {"cluster_pole": score}."""
    return {
        f"{cluster}_{pole}": score
        for cluster, poles in cluster_scores.items()
        for pole, score in poles.items()
    }


def _run_pipeline(
    text: str,
    language_code: str,
    window_size: int,
    stride: int,
    threshold: float,
    document_id: str,
) -> Dict[str, Any]:
    """
    Execute the full analysis pipeline for one document.

    The LanguageRouter provides the correct micro/macro analyzers for
    the given language; the dissonance engine always receives standardized
    six-vector micro scores so baselines remain cross-language comparable.
    """
    tokenizer      = RollingWindowTokenizer(window_size=window_size, stride=stride)
    micro_analyzer = _lang_router.micro(language_code)
    macro_analyzer = _lang_router.macro(language_code)
    _dissonance_engine.threshold = threshold

    windows = tokenizer.tokenize(text)
    window_results: List[Dict[str, Any]] = []

    # Compute the global waveform envelope ONCE from the entire document.
    # This 100-bucket compressed signal is returned at document level so the
    # UI can display the macro energy flow regardless of which window is active.
    global_envelope: List[float] = _somatic_engine.compute_global_envelope(
        text, language=language_code
    )

    for win in windows:
        micro_result   = micro_analyzer.analyze(win.text)
        macro_result   = macro_analyzer.analyze(win.text)
        somatic_result = _somatic_engine.analyze(win.text, language=language_code)
        # Per-window energy envelope (20 buckets) — computed via C++ _somatic_core
        win_envelope   = _somatic_engine.compute_global_envelope(
            win.text, language=language_code, n_buckets=20
        )

        # Standardized six-vector micro dict (works for all languages)
        micro_vectors = micro_result.filled_vectors()

        # Flatten macro cluster scores
        flat_macro = _flatten_macro(macro_result.cluster_scores)

        dis = _dissonance_engine.analyze_window(
            micro_scores=micro_vectors,
            macro_scores=flat_macro,
            document_id=document_id,
        )

        # Spatial localization — computed once per window from char offsets
        start_line = _char_to_line(text, win.start_char)
        end_line   = _char_to_line(text, win.end_char)
        start_snip, end_snip = _extract_snippets(text, win.start_char, win.end_char)

        raw_telem = _compute_window_telemetry(win.text, macro_result.hits)

        # ── v3.3: Steganographic anomaly scan (original text, all languages) ──
        raw_telem.update(_scan_hidden_unicode(win.text))

        # ── v3.3: Punctuation structural waveform (original text) ─────────────
        raw_telem["punctuation_waveform"] = _build_punct_waveform(win.text)

        # ── v3.3: Linguistic Entropy Engine (Split-Stream) ────────────────────
        # Stream A: win.text — untouched; used above for stego scan, punct waveform,
        #           C++ telemetry, and UI rendering.
        # Stream B: sanitized prose — Markdown structure stripped before NLP so
        #           headers/fences/bullets don't corrupt burstiness baselines.
        entropy_text = sanitize_for_entropy(win.text)
        lemmas = [h.lemma for h in macro_result.hits] if macro_result.hits else None
        raw_telem.update(compute_entropy_metrics(entropy_text, lemmas=lemmas))

        # ── Logographic structural override ───────────────────────────────────
        # For JA/ZH the micro analyzer computed native token counts via pykakasi
        # / jieba. Overwrite the Latin-regex counts so Total Words / Total Chars
        # in the UI reflect the actual native text, not the romanized proxy.
        if language_code in ("JA", "ZH") and micro_result.raw:
            for key in ("total_chars", "total_words", "avg_word_length"):
                if key in micro_result.raw:
                    raw_telem[key] = micro_result.raw[key]
        # ZH: pass stroke array through to the frontend Dual-Signal oscilloscope
        if language_code == "ZH":
            raw_telem["stroke_count_array"] = micro_result.raw.get(
                "stroke_count_array", []
            )

        # ── A–Z letter frequencies ─────────────────────────────────────────────
        # For JA/ZH: use the phonetic Romaji/Pinyin string so the UI letter
        # frequency list reflects the actual BPV alphabet, not native glyphs.
        # For all other languages: count directly from the window text.
        phonetic = micro_result.raw.get("phonetic_text", "") if language_code in ("JA", "ZH") else ""
        raw_telem["letter_frequencies"] = _compute_letter_freq(phonetic or win.text)

        window_results.append({
            "window_index":  win.index,
            "start_char":    win.start_char,
            "end_char":      win.end_char,
            "start_line":    start_line,
            "end_line":      end_line,
            "start_snippet": start_snip,
            "end_snippet":   end_snip,
            "reset_reason":  win.reset_reason,
            "language":      language_code,
            "micro": {
                "vectors": {k: round(v, 4) for k, v in micro_vectors.items()},
                "raw":     micro_result.raw,
            },
            "macro": {
                "total_words":    macro_result.total_words,
                "cluster_scores": {
                    cluster: {pole: round(score, 6) for pole, score in poles.items()}
                    for cluster, poles in macro_result.cluster_scores.items()
                },
                "semantic_hits":       len(macro_result.hits),
                "entity_polarity_map": macro_result.entity_polarity_map,
            },
            "somatic": {**somatic_result.to_dict(),
                        "window_envelope": [round(v, 4) for v in win_envelope]},
            "z_scores_micro": {k: round(v, 4) for k, v in dis.z_scores_micro.items()},
            "z_scores_macro": {k: round(v, 4) for k, v in dis.z_scores_macro.items()},
            "ema_snapshot":   {k: round(v, 4) for k, v in dis.ema_snapshot.items()},
            "dissonance_events": [
                {
                    "event_id":     e.event_id,
                    "timestamp":    e.timestamp,
                    "trigger_type": e.trigger_type,
                    "vectors":      e.vectors_involved,
                    "delta":        e.delta_score,
                    "conclusion":   e.algorithmic_conclusion,
                    "window_index":  win.index,
                    "start_line":    start_line,
                    "end_line":      end_line,
                    "start_snippet": start_snip,
                    "end_snippet":   end_snip,
                }
                for e in dis.dissonance_events
            ],
            "raw_telemetry": raw_telem,
        })

    return {
        "document_id":             document_id,
        "language":                language_code,
        "total_windows":           len(windows),
        "global_waveform_envelope": global_envelope,  # 100-float document-level envelope
        "windows":                 window_results,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze")
def analyze_text(req: AnalysisRequest) -> Dict[str, Any]:
    """Run the full psycholinguistic pipeline on submitted text."""
    if req.stride >= req.window_size:
        raise HTTPException(422, detail="stride must be strictly less than window_size")

    doc_id = req.document_id or f"doc_{uuid.uuid4().hex[:6]}"

    try:
        analysis = _run_pipeline(
            text=req.text,
            language_code=req.language_code.upper(),
            window_size=req.window_size,
            stride=req.stride,
            threshold=req.dissonance_threshold,
            document_id=doc_id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except RuntimeError as exc:
        # Raised by ModelRegistry when a spaCy model is missing
        raise HTTPException(503, detail=str(exc))

    # Persist to entity database
    entity = db.load_entity(DB_PATH)
    db.increment_document_count(entity)

    snapshot = _dissonance_engine.get_baseline_snapshot()
    db.update_baselines(entity, snapshot["micro"], snapshot["macro"])

    all_events = [ev for win in analysis["windows"] for ev in win["dissonance_events"]]
    db.append_dissonance_events(entity, all_events, doc_id)

    confidence = db.compute_confidence_score(entity)
    db.update_confidence_score(entity, confidence)
    db.save_entity(entity, DB_PATH)

    return analysis


@router.post("/control")
def seed_control_text(req: ControlTextRequest) -> Dict[str, Any]:
    """Seed engine baselines from a control / reference text."""
    try:
        micro_analyzer = _lang_router.micro(req.language_code.upper())
        macro_analyzer = _lang_router.macro(req.language_code.upper())
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc))

    tokenizer = RollingWindowTokenizer()
    windows   = tokenizer.tokenize(req.text)
    seeded    = 0

    for win in windows:
        micro  = micro_analyzer.analyze(win.text)
        macro  = macro_analyzer.analyze(win.text)
        _dissonance_engine.seed_baselines(
            micro_observations=micro.filled_vectors(),
            macro_observations=_flatten_macro(macro.cluster_scores),
        )
        seeded += 1

    snapshot = _dissonance_engine.get_baseline_snapshot()
    entity   = db.load_entity(DB_PATH)
    db.update_baselines(entity, snapshot["micro"], snapshot["macro"])
    db.save_entity(entity, DB_PATH)

    return {
        "status":            "baselines seeded",
        "language":          req.language_code.upper(),
        "windows_processed": seeded,
        "baseline_snapshot": snapshot,
    }


@router.get("/languages")
def list_languages() -> Dict[str, str]:
    """List all supported language codes and their names."""
    return SUPPORTED_LANGUAGES


@router.get("/entity")
def get_entity() -> Dict[str, Any]:
    return db.load_entity(DB_PATH)


@router.post("/entity")
def create_entity(req: EntityCreateRequest) -> Dict[str, Any]:
    entity = db.new_entity(
        primary_designator=req.primary_designator,
        known_aliases=req.known_aliases,
        suspected_agency=req.suspected_agency,
        steganography_risk=req.steganography_risk,
    )
    db.save_entity(entity, DB_PATH)
    return entity


@router.get("/entity/ledger")
def get_ledger() -> List[Dict[str, Any]]:
    return db.load_entity(DB_PATH).get("dissonance_ledger", [])


@router.delete("/entity/ledger")
def clear_ledger() -> Dict[str, str]:
    entity = db.load_entity(DB_PATH)
    entity["dissonance_ledger"] = []
    db.save_entity(entity, DB_PATH)
    return {"status": "ledger cleared"}


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status":         "ok",
        "engine":         "PsychoLinguistic Analysis Engine v2.0",
        "loaded_models":  __import__("language.registry", fromlist=["ModelRegistry"])
                          .ModelRegistry.loaded_models(),
        "languages":      list(SUPPORTED_LANGUAGES.keys()),
    }
