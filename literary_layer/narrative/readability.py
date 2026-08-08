"""
Literary Layer — Readability & Lexical Richness Utilities (Phase 4 / 6)
Standalone pure-Python functions; no spaCy dependency.

Phase 4 functions:
    count_syllables(word)          — English syllable heuristic
    flesch_reading_ease(…)         — Flesch Reading Ease (EN)
    compute_mattr(token_texts, …)  — Moving-Average Type-Token Ratio

Phase 6 additions:
    count_syllables_de(word)       — German syllable heuristic (umlaut-aware)
    count_syllables_fr(word)       — French syllable heuristic (accent-aware)
    amstad_readability(…)          — Amstad (1978) formula for German
    kandel_moles_readability(…)    — Kandel-Moles (1958) formula for French

All readability scores are calibrated "higher = easier" on their respective
original scales.  The three formulas are intentionally not collapsed into a
single interface so callers can choose the appropriate one explicitly.
"""
from __future__ import annotations

import re
from typing import List


# ══════════════════════════════════════════════════════════════════════════════
# ENGLISH (Phase 4)
# ══════════════════════════════════════════════════════════════════════════════

# Vowel letter groups for the EN heuristic (y counted as vowel)
_EN_VOWEL_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)


def count_syllables(word: str) -> int:
    """
    Count the syllables in an English word using a simple heuristic:
        1. Count vowel letter groups (each group ≈ one syllable nucleus).
        2. Subtract 1 if the word ends in a silent 'e' and has more than one vowel group.
        3. Return at least 1 for any non-empty word.

    Examples:
        "fire"    → 1   (fi-re; the final e is counted, subtract → 1)
        "flower"  → 2   (flo-wer)
        "eternal" → 3   (e-ter-nal)
        "through" → 1   (one vowel group 'ough')
    """
    clean = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not clean:
        return 0

    groups = len(_EN_VOWEL_RE.findall(clean))

    # Subtract silent terminal 'e', but only if doing so leaves ≥ 1 syllable
    if clean.endswith("e") and groups > 1:
        groups -= 1

    return max(1, groups)


def flesch_reading_ease(
    n_sentences: int,
    words: List[str],
    n_syllables: int,
) -> float:
    """
    Compute the Flesch Reading Ease score for English text.

    Formula:  206.835 − 1.015 × (words / sentences) − 84.6 × (syllables / words)

    Interpretation guide (Flesch 1948):
        90-100 — Very easy  (5th grade)
        70- 90 — Easy       (6th grade)
        60- 70 — Standard   (7th grade)
        50- 60 — Fairly difficult (high school)
        30- 50 — Difficult  (college)
         0- 30 — Very difficult (professional)
        <  0   — Extremely complex

    Args:
        n_sentences:  Number of sentences in the passage.
        words:        List of word strings (non-punctuation tokens).
        n_syllables:  Total syllable count across all words.

    Returns:
        Float score.  Returns 0.0 if the passage has no sentences or no words.
    """
    n_words = len(words)
    if n_sentences == 0 or n_words == 0:
        return 0.0

    asl = n_words / n_sentences    # average sentence length (words)
    asw = n_syllables / n_words    # average syllables per word

    return round(206.835 - 1.015 * asl - 84.6 * asw, 1)


# ══════════════════════════════════════════════════════════════════════════════
# GERMAN (Phase 6) — Amstad (1978)
# ══════════════════════════════════════════════════════════════════════════════

# German vowels including umlauts; y is a vowel in borrowed words (Lyrik, Physik)
_DE_VOWEL_RE = re.compile(r"[aeiouyäöüAEIOUYÄÖÜ]+", re.IGNORECASE)


def count_syllables_de(word: str) -> int:
    """
    Count syllables in a German word using a vowel-group heuristic.

    Differences from the English counter:
        • Umlaut vowels (ä, ö, ü) are included in the vowel set.
        • German terminal 'e' is often schwa and is generally pronounced, so
          we only subtract if the word ends in '-en', '-er', '-el' (the common
          unstressed suffixes) and the remaining stem still has ≥ 1 syllable.
          For a simple heuristic, we subtract terminal 'e' only when followed
          by 'n' or 'r' (so -en, -er lose the schwa count but -e alone retains
          it since German -e is usually pronounced as a full schwa).

    Examples:
        "Liebe"  → 2   (Lie-be — terminal 'e' is pronounced)
        "lesen"  → 2   (le-sen — terminal 'en' schwa elided in count)
        "Mutter" → 2   (Mut-ter — terminal 'er' schwa elided in count)
        "König"  → 2   (Kö-nig)
    """
    # Strip non-alphabetic characters; retain German letters
    clean = re.sub(r"[^a-zA-ZäöüÄÖÜß]", "", word).lower()
    # ß counts as a consonant (no vowel); replace for uniform counting
    clean = clean.replace("ß", "ss")
    if not clean:
        return 0

    groups = len(_DE_VOWEL_RE.findall(clean))

    # Subtract one syllable for silent schwa in common unstressed suffixes
    if (clean.endswith("en") or clean.endswith("er")) and groups > 1:
        groups -= 1

    return max(1, groups)


def amstad_readability(
    n_sentences: int,
    words: List[str],
    n_syllables: int,
) -> float:
    """
    Compute the Amstad (1978) readability score for German text.

    Amstad adapted the Flesch formula for German, recalibrating the constants
    against a German reference corpus:

        Score = 180 − ASL − 58.5 × ASW

    where ASL = average sentence length (words) and ASW = average syllables
    per word.

    Interpretation guide (same orientation as Flesch — higher = easier):
        > 70   — Very easy (newspaper, children's text)
        50–70  — Standard prose (novels, quality journalism)
        30–50  — Difficult (academic text)
        < 30   — Very difficult (scientific / legal German)

    Args:
        n_sentences:  Number of sentences.
        words:        List of word strings (alpha tokens).
        n_syllables:  Total German syllable count (use count_syllables_de).

    Returns:
        Float score.  Returns 0.0 for empty input.
    """
    n_words = len(words)
    if n_sentences == 0 or n_words == 0:
        return 0.0

    asl = n_words / n_sentences
    asw = n_syllables / n_words

    return round(180.0 - asl - 58.5 * asw, 1)


# ══════════════════════════════════════════════════════════════════════════════
# FRENCH (Phase 6) — Kandel-Moles (1958)
# ══════════════════════════════════════════════════════════════════════════════

# French vowels including all common accented forms and ligatures
_FR_VOWEL_RE = re.compile(
    r"[aeiouyàâéèêëîïôùûüœæÀÂÉÈÊËÎÏÔÙÛÜŒÆ]+",
    re.IGNORECASE,
)


def count_syllables_fr(word: str) -> int:
    """
    Count syllables in a French word using a vowel-group heuristic.

    French syllable counting differences from English:
        • Accented vowels (é, è, ê, à, â, î, ï, ô, ù, û, ü, œ, æ) are vowels.
        • Terminal 'e' is typically silent (mute 'e') → subtract 1 group if
          the word ends in 'e' (but NOT in 'ée', 'ue' as those are pronounced).
        • Terminal '-es' is also typically silent (plural marker).
        • Minimum 1 syllable.

    Examples:
        "forte"   → 1   (terminal mute e subtracted; for-te → 1)
        "armée"   → 2   (ar-mée — accented é is pronounced)
        "courageux" → 3 (cou-ra-geux)
        "fleuve"  → 1   (fleu-ve — mute e subtracted)
    """
    clean = re.sub(r"[^a-zA-ZàâéèêëîïôùûüœæÀÂÉÈÊËÎÏÔÙÛÜŒÆ]", "", word).lower()
    if not clean:
        return 0

    groups = len(_FR_VOWEL_RE.findall(clean))

    # Mute terminal 'e' (but keep accented 'é', 'è', etc. — they're pronounced)
    if clean.endswith("e") and not clean.endswith(("ée", "ie")) and groups > 1:
        groups -= 1

    # Terminal '-es' (plural) is also often silent
    if clean.endswith("es") and not clean.endswith(("ées", "ies")) and groups > 1:
        groups -= 1

    return max(1, groups)


def kandel_moles_readability(
    n_sentences: int,
    words: List[str],
    n_syllables: int,
) -> float:
    """
    Compute the Kandel-Moles (1958) readability score for French text.

    Kandel and Moles adapted the Flesch formula for French, recalibrating
    against a French reference corpus:

        Score = 207 − 1.015 × ASL − 73.6 × ASW

    where ASL = average sentence length (words) and ASW = average syllables
    per word.

    Interpretation guide (higher = easier):
        > 65   — Very easy (simple French prose, press)
        50–65  — Fairly easy (novels, standard French)
        35–50  — Difficult (complex prose, essays)
        < 35   — Very difficult (academic / scientific French)

    Args:
        n_sentences:  Number of sentences.
        words:        List of word strings (alpha tokens).
        n_syllables:  Total French syllable count (use count_syllables_fr).

    Returns:
        Float score.  Returns 0.0 for empty input.
    """
    n_words = len(words)
    if n_sentences == 0 or n_words == 0:
        return 0.0

    asl = n_words / n_sentences
    asw = n_syllables / n_words

    return round(207.0 - 1.015 * asl - 73.6 * asw, 1)


# ── Moving-Average Type-Token Ratio ───────────────────────────────────────────

def compute_mattr(token_texts: List[str], window_size: int = 100) -> float:
    """
    Compute the Moving-Average Type-Token Ratio (MATTR; Covington & McFall 2010).

    MATTR averages TTR over sliding windows of *window_size* tokens, which
    removes the well-known bias of raw TTR against longer texts.

    Args:
        token_texts:  List of token strings (lowercased content words recommended).
        window_size:  Number of tokens per sliding window (default 100).

    Returns:
        Float in [0, 1].  Higher values indicate richer, more varied vocabulary.
        Returns raw TTR when the token list is shorter than *window_size*.
    """
    n = len(token_texts)
    if n == 0:
        return 0.0

    if n < window_size:
        # Not enough tokens for a full window — fall back to single-pass TTR
        return len(set(t.lower() for t in token_texts)) / n

    ttrs: List[float] = []
    for i in range(n - window_size + 1):
        window = token_texts[i : i + window_size]
        types  = len(set(t.lower() for t in window))
        ttrs.append(types / window_size)

    return sum(ttrs) / len(ttrs)
