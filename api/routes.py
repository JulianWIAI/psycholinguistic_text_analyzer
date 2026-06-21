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
import traceback
import uuid
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import database.schema as db
from dissonance.engine import DissonanceEngine
from entropy_engine import compute_entropy_metrics, sanitize_for_entropy
from language.router import LanguageRouter, SUPPORTED_LANGUAGES
from micro_layer.lexical_affinity import LexicalAffinityRadar
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

# Languages for which Lexical Affinity Radar is meaningful (Latin script, spaCy POS)
_LAR_LANGS = frozenset({"EN", "DE", "ES", "FR"})

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


# Canonical 33-letter Cyrillic alphabet in dictionary order (А–Е, Ё, Ж–Я)
_CYRILLIC_UPPER: List[str] = (
    [chr(c) for c in range(0x0410, 0x0416)]   # А Б В Г Д Е
    + [chr(0x0401)]                             # Ё
    + [chr(c) for c in range(0x0416, 0x0430)]  # Ж З И Й К … Я
)

# Arabic 28-letter abjadi sequence (mirrors ar::AR_GLYPH in ar_bpv_table.h)
_ARABIC_ABJAD: List[str] = [
    "ا","ب","ت","ث","ج","ح","خ","د","ذ","ر","ز","س","ش","ص","ض","ط","ظ","ع","غ","ف","ق","ك","ل","م","ن","ه","و","ي",
]
# Farsi 32-letter sequence (28 Arabic + پ چ ژ گ)
_FARSI_ABJAD: List[str] = _ARABIC_ABJAD + ["پ","چ","ژ","گ"]

# Korean 24-bin Jamo sequence (14 consonants + 10 vowels, mirrors ko::KO_GLYPH)
_KOREAN_JAMO_24: List[str] = [
    "ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ",
    "ㅏ","ㅑ","ㅓ","ㅕ","ㅗ","ㅛ","ㅜ","ㅠ","ㅡ","ㅣ",
]

# Onset Jamo range U+1100–U+1112 → bin 0–13 (14 basic consonant bins)
# Each onset maps to the same 24-bin index as in ko_bpv_table.h ONSET_TABLE.
# Tense consonants fold to base bin; compound codas handled via syllable decompose.
_KO_ONSET_TO_BIN: Dict[int, int] = {
    0x1100:  0, 0x1101:  0,  # ㄱ ㄲ→ㄱ
    0x1102:  1,              # ㄴ
    0x1103:  2, 0x1104:  2,  # ㄷ ㄸ→ㄷ
    0x1105:  3,              # ㄹ
    0x1106:  4,              # ㅁ
    0x1107:  5, 0x1108:  5,  # ㅂ ㅃ→ㅂ
    0x1109:  6, 0x110A:  6,  # ㅅ ㅆ→ㅅ
    0x110B:  7,              # ㅇ
    0x110C:  8, 0x110D:  8,  # ㅈ ㅉ→ㅈ
    0x110E:  9,              # ㅊ
    0x110F: 10,              # ㅋ
    0x1110: 11,              # ㅌ
    0x1111: 12,              # ㅍ
    0x1112: 13,              # ㅎ
}
# Nucleus Jamo range U+1161–U+1175 → bin 14–23 (10 basic vowel bins)
_KO_NUCLEUS_TO_BIN: Dict[int, int] = {
    0x1161: 14, 0x1162: 14,  # ㅏ ㅐ→ㅏ
    0x1163: 15, 0x1164: 15,  # ㅑ ㅒ→ㅑ
    0x1165: 16, 0x1166: 16,  # ㅓ ㅔ→ㅓ
    0x1167: 17, 0x1168: 17,  # ㅕ ㅖ→ㅕ
    0x1169: 18, 0x116A: 18, 0x116B: 18, 0x116C: 18,  # ㅗ ㅘ ㅙ ㅚ→ㅗ
    0x116D: 19,              # ㅛ
    0x116E: 20, 0x116F: 20, 0x1170: 20, 0x1171: 20,  # ㅜ ㅝ ㅞ ㅟ→ㅜ
    0x1172: 21,              # ㅠ
    0x1173: 22, 0x1174: 22,  # ㅡ ㅢ→ㅡ
    0x1175: 23,              # ㅣ
}
# Coda → consonant bin (subset; non-null codas fold to their primary consonant bin)
_KO_CODA_TO_BIN: Dict[int, int] = {
    0x11A8:  0, 0x11A9:  0,  # ㄱ ㄲ
    0x11AA:  6,              # ㄳ→ㅅ
    0x11AB:  1, 0x11AC:  1, 0x11AD:  1,  # ㄴ ㄵ ㄶ
    0x11AE:  2,              # ㄷ
    0x11AF:  3, 0x11B0:  3, 0x11B1:  3, 0x11B2:  3,
    0x11B3:  3, 0x11B4:  3, 0x11B5:  3, 0x11B6:  3,  # ㄹ cluster
    0x11B7:  4,              # ㅁ
    0x11B8:  5, 0x11B9:  5,  # ㅂ ㅄ
    0x11BA:  6, 0x11BB:  6,  # ㅅ ㅆ
    0x11BC:  7,              # ㅇ
    0x11BD:  8,              # ㅈ
    0x11BE:  9,              # ㅊ
    0x11BF: 10,              # ㅋ
    0x11C0: 11,              # ㅌ
    0x11C1: 12,              # ㅍ
    0x11C2: 13,              # ㅎ
}

# Arabic punctuation bytes for the Python-side waveform builder (2-byte UTF-8)
_PUNCT_UTF8_2: Dict[bytes, int] = {
    b"\xd8\x8c": 1,  # ، U+060C Arabic Comma → magnitude 1
    b"\xd8\x9f": 4,  # ؟ U+061F Arabic Question Mark → magnitude 4
}


def _compute_cyrillic_freq(text: str) -> Dict[str, int]:
    """Return a full 33-key Cyrillic frequency dict (А–Я including Ё)."""
    freq: Dict[str, int] = {ch: 0 for ch in _CYRILLIC_UPPER}
    for ch in text.upper():
        if ch in freq:
            freq[ch] += 1
    return freq


def _compute_korean_freq(text: str) -> Dict[str, int]:
    """
    Return a 24-key Jamo frequency dict by decomposing each Hangul syllable block
    (U+AC00–U+D7A3) and mapping its Onset/Nucleus/Coda to the 24 basic bins.
    Non-syllabic Hangul Jamo (standalone) are also counted if present.
    """
    freq: Dict[str, int] = {g: 0 for g in _KOREAN_JAMO_24}
    _SYL_START = 0xAC00
    _SYL_END   = 0xD7A3

    def _inc(bin_idx: int) -> None:
        if 0 <= bin_idx < 24:
            freq[_KOREAN_JAMO_24[bin_idx]] += 1

    for ch in text:
        cp = ord(ch)
        if _SYL_START <= cp <= _SYL_END:
            idx     = cp - _SYL_START
            onset   = idx // (21 * 28)
            nucleus = (idx % (21 * 28)) // 28
            coda    = idx % 28
            onset_cp   = 0x1100 + onset
            nucleus_cp = 0x1161 + nucleus
            if onset_cp in _KO_ONSET_TO_BIN:
                _inc(_KO_ONSET_TO_BIN[onset_cp])
            if nucleus_cp in _KO_NUCLEUS_TO_BIN:
                _inc(_KO_NUCLEUS_TO_BIN[nucleus_cp])
            if coda > 0:
                coda_cp = 0x11A7 + coda
                if coda_cp in _KO_CODA_TO_BIN:
                    _inc(_KO_CODA_TO_BIN[coda_cp])
        elif cp in _KO_ONSET_TO_BIN:
            _inc(_KO_ONSET_TO_BIN[cp])
        elif cp in _KO_NUCLEUS_TO_BIN:
            _inc(_KO_NUCLEUS_TO_BIN[cp])
        elif cp in _KO_CODA_TO_BIN:
            _inc(_KO_CODA_TO_BIN[cp])
    return freq


def _compute_arabic_freq(text: str, is_farsi: bool = False) -> Dict[str, int]:
    """
    Return an Abjad frequency dict: 28 keys for AR, 32 keys for FA.
    Counts each canonical consonant; diacritics and Alef variants are folded
    into their canonical form (all Alef variants → ا, ى → ي).
    """
    alphabet = _FARSI_ABJAD if is_farsi else _ARABIC_ABJAD
    freq: Dict[str, int] = {ch: 0 for ch in alphabet}

    # Alef variant mapping: آ أ إ ٱ ﺃ → ا
    _ALEF_VARIANTS = {"آ", "أ", "إ", "ٱ"}
    # Alef Maqsura ى → ي
    _YA_VARIANTS   = {"ى"}
    # Waw+Hamza ؤ → و
    _WAW_VARIANTS  = {"ؤ"}
    # Ya+Hamza ئ → ي
    _YAH_VARIANTS  = {"ئ"}

    for ch in text:
        if ch in _ALEF_VARIANTS:
            freq["ا"] = freq.get("ا", 0) + 1
        elif ch in _YA_VARIANTS or ch in _YAH_VARIANTS:
            freq["ي"] = freq.get("ي", 0) + 1
        elif ch in _WAW_VARIANTS:
            freq["و"] = freq.get("و", 0) + 1
        elif ch in freq:
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
        # 3-byte sequences (en/em dash)
        if i + 2 < n:
            tri = bytes(raw[i:i+3])
            if tri in _PUNCT_UTF8:
                wave.append(_PUNCT_UTF8[tri])
                i += 3
                continue
        # 2-byte sequences: Arabic comma ، (D8 8C) and question mark ؟ (D8 9F)
        if i + 1 < n:
            bi = bytes(raw[i:i+2])
            if bi in _PUNCT_UTF8_2:
                wave.append(_PUNCT_UTF8_2[bi])
                i += 2
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

        # ── RU override — replace Latin-regex telemetry with Cyrillic C++ output ──
        # _compute_window_telemetry uses [A-Za-z]+ regex → finds nothing in Cyrillic
        # text. The C++ analyze_ru() provides correct Cyrillic counts in micro_result.raw.
        if language_code == "RU" and micro_result.raw:
            for key in ("total_chars", "total_words", "avg_word_length",
                        "top_micro_chars", "double_letter_anomalies", "structural_waveform"):
                if key in micro_result.raw:
                    raw_telem[key] = micro_result.raw[key]

        # ── AR / FA override — Abjad C++ telemetry replaces Latin-regex counts ──
        # Same rationale as RU: [A-Za-z]+ finds nothing in Arabic/Farsi script.
        # psycho_core.analyze_ar() / analyze_fa() provide correct counts.
        if language_code in ("AR", "FA") and micro_result.raw:
            for key in ("total_chars", "total_words", "avg_word_length",
                        "top_micro_chars", "double_letter_anomalies", "structural_waveform"):
                if key in micro_result.raw:
                    raw_telem[key] = micro_result.raw[key]

        # ── KO override — Hangul Jamo C++ telemetry replaces Latin-regex counts ──
        # [A-Za-z]+ finds nothing in Hangul text. psycho_core.analyze_ko() provides
        # Jamo-level counts; total_chars is replaced with native syllable count by
        # KoreanOrthographicAnalyzer._parse_windows() before reaching here.
        if language_code == "KO" and micro_result.raw:
            for key in ("total_chars", "total_words", "avg_word_length",
                        "top_micro_chars", "double_letter_anomalies", "structural_waveform"):
                if key in micro_result.raw:
                    raw_telem[key] = micro_result.raw[key]

        # ── Lexical Affinity Radar (Latin-script languages only) ─────────────
        # Runs spaCy POS tagging on the window text via the macro analyzer's
        # already-loaded NLP pipeline to avoid a second model load.
        if language_code in _LAR_LANGS:
            try:
                spacy_doc = macro_analyzer._nlp(win.text)
                lar = LexicalAffinityRadar(spacy_doc, macro_result.cluster_scores)
                lexical_affinity = lar.analyze()
            except Exception:
                lexical_affinity = None
        else:
            lexical_affinity = None

        # ── Letter frequencies ────────────────────────────────────────────────
        # RU:     count Cyrillic А–Я directly from window text.
        # AR:     count 28 Arabic consonants (abjadi order) from window text.
        # FA:     count 32 Farsi consonants (abjadi + پچژگ) from window text.
        # JA/ZH:  use phonetic Romaji/Pinyin string for the Latin BPV alphabet.
        # Others: count A–Z directly from window text.
        if language_code == "RU":
            raw_telem["letter_frequencies"] = _compute_cyrillic_freq(win.text)
        elif language_code == "AR":
            raw_telem["letter_frequencies"] = _compute_arabic_freq(win.text, is_farsi=False)
        elif language_code == "FA":
            raw_telem["letter_frequencies"] = _compute_arabic_freq(win.text, is_farsi=True)
        elif language_code == "KO":
            raw_telem["letter_frequencies"] = _compute_korean_freq(win.text)
        else:
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
            "raw_telemetry":     raw_telem,
            "lexical_affinity":  lexical_affinity,
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
        raise HTTPException(503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(500, detail=f"{type(exc).__name__}: {exc}")

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

    try:
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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")


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
