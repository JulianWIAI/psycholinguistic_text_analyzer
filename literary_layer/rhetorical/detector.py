"""
Literary Layer — Rhetorical Device Detector (Phase 5 / 6)
Stateless orchestrator that runs all per-device detectors for a given language
and returns a single flat list of LiteraryFinding objects sorted by position.

Device coverage per language:

    ┌─────────────────────────┬────┬────┬────┐
    │ Device                  │ EN │ DE │ FR │
    ├─────────────────────────┼────┼────┼────┤
    │ Alliteration  (phonetic)│  ✓ │  ✓ │  ✓ │
    │ Assonance     (phonetic)│  ✓ │  ✓ │  ✓ │
    │ Anaphora   (structural) │  ✓ │  ✓ │  ✓ │
    │ Epistrophe (structural) │  ✓ │  ✓ │  ✓ │
    │ Simile        (semantic)│  ✓ │  ✓ │  ✓ │
    │ Rhetorical Q  (semantic)│  ✓ │  ✓ │  ✓ │
    │ Personification(figura.)│  ✓ │    │    │
    │ Oxymoron      (figura.) │  ✓ │    │    │
    │ Antithesis    (figura.) │  ✓ │  ✓ │  ✓ │
    │ Polysyndeton  (rhythmic)│  ✓ │  ✓ │  ✓ │
    │ Asyndeton     (rhythmic)│  ✓ │  ✓ │  ✓ │
    │ Hyperbole     (rhythmic)│  ✓ │    │    │
    │ Litotes       (rhythmic)│  ✓ │    │    │
    └─────────────────────────┴────┴────┴────┘

Individual detectors self-gate on language — returning [] for unsupported codes —
so this orchestrator simply calls all detectors for every supported language and
lets each one decide what to emit.

The detector carries no per-document state and is safe to reuse as a
module-level singleton across concurrent requests.
"""
from __future__ import annotations

from typing import List

from literary_layer.base import LiteraryFinding

# ── Phase 2 detectors ──────────────────────────────────────────────────────────
from literary_layer.rhetorical.phonetic   import detect_alliteration
from literary_layer.rhetorical.structural import detect_anaphora, detect_epistrophe
from literary_layer.rhetorical.semantic   import detect_simile, detect_rhetorical_question

# ── Phase 5 detectors ──────────────────────────────────────────────────────────
from literary_layer.rhetorical.phonetic   import detect_assonance
from literary_layer.rhetorical.figurative import (
    detect_personification,
    detect_oxymoron,
    detect_antithesis,
)

# ── Phase 6 detectors ──────────────────────────────────────────────────────────
from literary_layer.rhetorical.rhythmic import (
    detect_polysyndeton,
    detect_asyndeton,
    detect_hyperbole,
    detect_litotes,
)

# Languages for which at least one detector is available.
# Returning [] for unsupported languages means the caller never needs to branch
# on language; it simply gets no findings.
_SUPPORTED_LANGUAGES: frozenset = frozenset({"EN", "DE", "FR"})


class RhetoricalDetector:
    """
    Runs all enabled rhetorical device detectors for a single analysis window.

    Each detector function accepts a *language* parameter and self-gates by
    returning an empty list for languages it does not support — so this class
    calls every detector unconditionally and merges the results.

    Usage:
        detector = RhetoricalDetector()          # create once as a singleton
        findings = detector.detect(doc, text, start_char, line_index, "DE")
    """

    def detect(
        self,
        doc,                   # spaCy Doc (pre-parsed by the macro analyzer)
        raw_text: str,         # window.text (available for fallback regex patterns)
        start_char: int,       # window.start_char — absolute offset in full document
        line_index: List[int],
        language: str,
    ) -> List[LiteraryFinding]:
        """
        Run all device detectors that are available for *language* and return
        a unified list sorted by (line_number, char_start).

        Args:
            doc:         Pre-parsed spaCy Doc for the window text.
            raw_text:    Raw window text, passed to regex-based detectors.
            start_char:  Absolute offset of this window's first character in the
                         full original document.
            line_index:  Pre-built list from build_line_index(full_document_text).
            language:    ISO language code, e.g. "EN", "DE", "FR".

        Returns:
            Sorted list of LiteraryFinding objects; empty list for unsupported langs.
        """
        if language not in _SUPPORTED_LANGUAGES:
            return []

        findings: List[LiteraryFinding] = []

        # ── Phase 2 / 5: Phonetic devices ──────────────────────────────────────
        # detect_alliteration and detect_assonance both accept language param
        # and load the correct VOWELS / SKIP_POS from get_patterns(language).
        findings.extend(detect_alliteration(doc, start_char, line_index, language))
        findings.extend(detect_assonance(   doc, start_char, line_index, language))

        # ── Phase 2 / 5: Structural devices ────────────────────────────────────
        # Anaphora and epistrophe are logically language-agnostic (lemma-based);
        # language param selects the correct SKIP_POS_BOUNDARY constant.
        findings.extend(detect_anaphora(    doc, start_char, line_index, language))
        findings.extend(detect_epistrophe(  doc, start_char, line_index, language))

        # ── Phase 2 / 5: Semantic devices ──────────────────────────────────────
        # Simile and rhetorical_question use language-specific particles /
        # interrogative word sets from get_patterns(language).
        findings.extend(detect_simile(             doc, start_char, line_index, language))
        findings.extend(detect_rhetorical_question(doc, start_char, line_index, language))

        # ── Phase 5: Figurative devices ────────────────────────────────────────
        # Personification and oxymoron are EN-only (self-gate on language != "EN").
        # Antithesis uses language-aware CONTRASTIVE_CONJ via get_patterns().
        findings.extend(detect_personification(doc, start_char, line_index, language))
        findings.extend(detect_oxymoron(       doc, start_char, line_index, language))
        findings.extend(detect_antithesis(     doc, start_char, line_index, language))

        # ── Phase 6: Rhythmic devices ───────────────────────────────────────────
        # Polysyndeton and asyndeton are language-aware (language-specific
        # conjunction sets via get_patterns()).
        # Hyperbole and litotes are EN-only (self-gate on language != "EN").
        findings.extend(detect_polysyndeton(doc, start_char, line_index, language))
        findings.extend(detect_asyndeton(   doc, start_char, line_index, language))
        findings.extend(detect_hyperbole(   doc, start_char, line_index, language))
        findings.extend(detect_litotes(     doc, start_char, line_index, language))

        # Sort by document position so the UI renders findings top-to-bottom
        findings.sort(key=lambda f: (f.line_number, f.char_start))
        return findings
