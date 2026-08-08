"""
Literary Layer — LiteraryAnalyzer
Public entry point for the entire literary analysis pipeline.

Accepts an already-parsed spaCy Doc (reused from the macro layer to avoid
double parsing) plus the window's metadata and returns a LiteraryResult that
is JSON-serialisable via .to_dict().

Instantiate once as a module-level singleton in api/routes.py and reuse
across all windows and requests — the analyzer carries no per-document state.

    # In api/routes.py:
    _literary_analyzer = LiteraryAnalyzer()

    # Inside the per-window loop (after spacy_doc is already available):
    literary_result = _literary_analyzer.analyze(
        doc        = spacy_doc,
        raw_text   = win.text,
        start_char = win.start_char,
        line_index = line_index,    # built once per document before the loop
        language   = language_code,
    )

Phase roadmap:
    Phase 2 — rhetorical_findings: alliteration, anaphora,
               epistrophe, simile, rhetorical_question  (EN only)
    Phase 3 — word_fields: FieldScorer + 14 domain seed dicts (EN/DE/FR)
    Phase 4 — narrative: voice, tense, direct speech, MATTR, readability
    Phase 5 — rhetorical extended to DE/FR; assonance, personification,
               oxymoron, antithesis added
    Phase 6 — polysyndeton, asyndeton, hyperbole, litotes; DE/FR readability
    Phase 7 — argumentation: Ethos / Pathos / Logos sentence classification
    Phase 8 — stylometry: Burrows'-Delta function-word profile, punctuation
               ratios, sentence-length stats, hapax ratio
    Phase 9 — lexical richness: 10-point MATTR waveform, hapax ratio,
               Heaps'-law comparison, register-shift detection
"""
from __future__ import annotations

from typing import List

from literary_layer.base import LiteraryResult

# ── Phase 2 / 5 / 6: Rhetorical devices ───────────────────────────────────────
from literary_layer.rhetorical.detector import RhetoricalDetector

# ── Phase 3: Semantic word fields ─────────────────────────────────────────────
from literary_layer.word_fields.field_scorer import FieldScorer

# ── Phase 4 / 6: Narrative metrics + DE/FR readability ───────────────────────
from literary_layer.narrative.analyzer import NarrativeAnalyzer

# ── Phase 7: Argumentation mining ─────────────────────────────────────────────
from literary_layer.argumentation.detector import ArgumentationDetector

# ── Phase 8: Stylometric fingerprinting ───────────────────────────────────────
from literary_layer.stylometry.fingerprinter import StylometricFingerprinter

# ── Phase 9: Lexical richness progression ─────────────────────────────────────
from literary_layer.lexical_richness.progression import LexicalRichnessAnalyzer


class LiteraryAnalyzer:
    """
    Stateless facade over all literary sub-analysers (Phases 2–9).

    The object is thread-safe because it holds no mutable state; only the
    sub-analyser singletons are stored, all of which are likewise stateless.
    FieldScorer caches per-language centroid vectors internally after the
    first call so centroid computation runs at most once per language per
    server lifetime.

    Sub-analysers in __init__ (in pipeline order):
        _rhetorical   — RhetoricalDetector (Phases 2/5/6)
        _field_scorer — FieldScorer        (Phase 3)
        _narrative    — NarrativeAnalyzer  (Phase 4/6)
        _argumentation— ArgumentationDetector (Phase 7)
        _stylometry   — StylometricFingerprinter (Phase 8)
        _lexical      — LexicalRichnessAnalyzer  (Phase 9)
    """

    def __init__(self) -> None:
        self._rhetorical    = RhetoricalDetector()
        self._field_scorer  = FieldScorer()
        self._narrative     = NarrativeAnalyzer()
        self._argumentation = ArgumentationDetector()   # Phase 7
        self._stylometry    = StylometricFingerprinter()  # Phase 8
        self._lexical       = LexicalRichnessAnalyzer()   # Phase 9

    def analyze(
        self,
        doc,               # spaCy Doc produced by the macro analyzer for this window
        raw_text: str,     # window.text — kept for regex-based device detectors
        start_char: int,   # window.start_char — absolute offset into the full document
        line_index: List[int],
        language: str,
    ) -> LiteraryResult:
        """
        Run all literary detectors for *language* and return a LiteraryResult.

        Args:
            doc:         Pre-parsed spaCy Doc (reused from macro layer — no
                         extra parse cost).
            raw_text:    Raw window text string.
            start_char:  Absolute char offset of the window start in the
                         original document.
            line_index:  List of char offsets where each document line begins,
                         built once per document with build_line_index().
            language:    ISO language code ("EN", "DE", "FR", …).

        Returns:
            LiteraryResult with all phase fields populated, serialisable via
            .to_dict().
        """
        # Phase 2 / 5 / 6 — rhetorical devices (EN/DE/FR)
        rhetorical_findings = self._rhetorical.detect(
            doc        = doc,
            raw_text   = raw_text,
            start_char = start_char,
            line_index = line_index,
            language   = language,
        )

        # Phase 3 — semantic word fields (EN/DE/FR; silently empty otherwise)
        word_fields = self._field_scorer.score(
            doc        = doc,
            start_char = start_char,
            line_index = line_index,
            language   = language,
        )

        # Phase 4 / 6 — narrative metrics + language-aware readability
        narrative = self._narrative.analyze(
            doc      = doc,
            raw_text = raw_text,
            language = language,
        )

        # Phase 7 — Ethos / Pathos / Logos sentence classification (EN/DE/FR)
        argumentation = self._argumentation.detect(
            doc        = doc,
            start_char = start_char,
            line_index = line_index,
            language   = language,
        )

        # Phase 8 — Burrows'-Delta stylometric fingerprint (all languages)
        stylometry = self._stylometry.compute(
            doc      = doc,
            language = language,
        )

        # Phase 9 — Lexical richness waveform (language-agnostic)
        lexical_progression = self._lexical.analyze(doc)

        return LiteraryResult(
            rhetorical_findings = rhetorical_findings,
            word_fields         = word_fields,
            narrative           = narrative,
            argumentation       = argumentation,
            stylometry          = stylometry,
            lexical_progression = lexical_progression,
        )
