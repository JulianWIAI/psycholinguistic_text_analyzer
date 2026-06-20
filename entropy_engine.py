"""
MODULE — Linguistic Entropy Engine (v3.3)
Detects AI-generated and heavily sanitized text via syntactic physics.

Metrics
-------
burstiness          σ of sentence lengths (word count per sentence).
                    Humans produce irregular sentence rhythms (σ ≈ 6–12);
                    AI-generated text is unusually flat (σ ≈ 0–3).

lexical_entropy     unique_lemmas / total_words.
                    AI tends toward a broad but shallow vocabulary (0.65–0.85);
                    human writing is more anchored to topic-specific repetition.

ai_probability_score  composite 0.0–1.0 signal:
                    low burstiness (flat wave) × high lexical entropy ≈ AI.
                    Weight: burstiness 65 %, lexical entropy 35 %.

Split-Stream Pipeline
---------------------
Stream A  Raw text — passed untouched to C++ telemetry, steganography scanner,
          punctuation waveform, and UI rendering.

Stream B  Sanitized prose — produced by sanitize_for_entropy(); fed exclusively
          to compute_entropy_metrics() for burstiness and lexical entropy.
          Markdown structure (headers, fences, bullets, blockquotes) is removed
          so syntactic physics reflects authorial rhythm, not document formatting.
          Period injection closes unpunctuated lines before whitespace collapse so
          that spaCy's sentence boundary detector never stitches a header or bullet
          item into the following sentence, preventing artificial burstiness inflation.
"""

import math
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Stream A helpers (unchanged — operate on raw text)
# ---------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_RE    = re.compile(r"[A-Za-z']+")

# ---------------------------------------------------------------------------
# Stream B — Markdown sanitizer (pre-compiled for zero per-call overhead)
# ---------------------------------------------------------------------------

# 1. Fenced code blocks  (``` ... ```)  — removed entirely; DOTALL so newlines match
_RE_FENCE          = re.compile(r"```.*?```", re.DOTALL)
# 2. Inline code  (`...`)
_RE_INLINE         = re.compile(r"`[^`\n]+`")
# 3. Markdown structural line prefixes  (# ## * - > => | followed by optional space)
#    Anchored to line-start with re.MULTILINE so each line is handled independently.
_RE_MD_PFX         = re.compile(r"^[ \t]*(?:#{1,6}|[*\->|]|=>)[ \t]*", re.MULTILINE)
# 4. Horizontal rules (--- / *** / ===)
_RE_HR             = re.compile(r"^[ \t]*[-*=]{3,}[ \t]*$", re.MULTILINE)
# 5. Period injection — must run AFTER prefix stripping and BEFORE whitespace collapse.
#    Matches the last non-whitespace character on any line that does NOT already end
#    with a terminal punctuation mark (.  !  ?).  Trailing spaces/tabs before the
#    newline are consumed by [ \t]* so the injected period attaches directly to the
#    final alphanumeric character rather than floating after whitespace.
#    $ anchors to the position just before \n (MULTILINE), so \n itself is not
#    consumed — the boundary survives for the next substitution to see.
_RE_INJECT_PERIOD  = re.compile(r"([^\s.!?])[ \t]*$", re.MULTILINE)
# 6. Remaining Markdown emphasis / bold / strikethrough delimiters
_RE_EMPH           = re.compile(r"[*_~]{1,3}")
# 7. Collapse all whitespace runs (spaces, tabs, newlines) into a single space
_RE_WS             = re.compile(r"\s+")


def sanitize_for_entropy(text: str) -> str:
    """
    Return a clean prose string (Stream B) suitable for NLP sentence segmentation.

    The original *text* (Stream A) is never modified — this function returns a
    new string.

    Pipeline order is load-bearing:
      1. Fences before inline code — prevents triple-backtick openers from being
         partially consumed by the single-backtick pattern.
      2. Prefix stripping before period injection — ensures we evaluate actual
         prose characters, not stripped structural symbols (#, *, -, etc.).
      3. Period injection before whitespace collapse — \n boundaries must still
         exist for the MULTILINE $ anchor to fire correctly.
      4. Emphasis stripping after injection — any * left at a line end receives a
         period first (→ `*.`), then the * is removed, leaving the period intact.
    """
    s = _RE_FENCE.sub(" ", text)              # fenced blocks → space
    s = _RE_INLINE.sub(" ", s)                # inline code → space
    s = _RE_HR.sub(" ", s)                    # horizontal rules → space
    s = _RE_MD_PFX.sub("", s)                 # strip structural line prefixes
    s = _RE_INJECT_PERIOD.sub(r"\1.", s)      # close unpunctuated lines with a period
    s = _RE_EMPH.sub("", s)                   # strip bold/italic/strike delimiters
    s = _RE_WS.sub(" ", s)                    # collapse all whitespace
    return s.strip()


# ---------------------------------------------------------------------------
# Core metric computation — expects Stream B text
# ---------------------------------------------------------------------------

def compute_entropy_metrics(
    text: str,
    lemmas: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Parameters
    ----------
    text   : sanitized prose string (Stream B) used for sentence segmentation
             and fallback word count.
    lemmas : lemmatized content tokens from spaCy (preferred for lexical entropy);
             when None, raw alphabetic tokens from *text* are used instead.

    Returns
    -------
    dict with keys: sentence_count, burstiness, lexical_entropy, ai_probability_score
    """
    # ── Sentence segmentation ────────────────────────────────────────────────
    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    if not sentences:
        sentences = [text.strip()] if text.strip() else [""]

    lengths = [len(_WORD_RE.findall(s)) for s in sentences if _WORD_RE.search(s)]
    if not lengths:
        lengths = [0]

    # ── Burstiness: σ of per-sentence word counts ────────────────────────────
    if len(lengths) < 2:
        burstiness = 0.0
    else:
        mean     = sum(lengths) / len(lengths)
        variance = sum((ln - mean) ** 2 for ln in lengths) / (len(lengths) - 1)
        burstiness = math.sqrt(max(0.0, variance))

    # ── Lexical entropy: unique / total (lemma-level when available) ─────────
    if lemmas:
        total_words  = len(lemmas)
        unique_words = len(set(lemmas))
    else:
        words        = _WORD_RE.findall(text.lower())
        total_words  = len(words)
        unique_words = len(set(words))

    lexical_entropy = unique_words / max(1, total_words)

    # ── AI probability composite ─────────────────────────────────────────────
    # Burstiness component: σ ≥ 10 → fully human; σ = 0 → fully AI
    burst_ai   = max(0.0, 1.0 - burstiness / 10.0)
    # Lexical entropy component: entropy ≤ 0.4 → human anchor; ≥ 0.8 → AI range
    entropy_ai = max(0.0, min(1.0, (lexical_entropy - 0.4) / 0.4))
    ai_probability = round(burst_ai * 0.65 + entropy_ai * 0.35, 4)

    return {
        "sentence_count":       len(lengths),
        "burstiness":           round(burstiness, 4),
        "lexical_entropy":      round(lexical_entropy, 4),
        "ai_probability_score": ai_probability,
    }
