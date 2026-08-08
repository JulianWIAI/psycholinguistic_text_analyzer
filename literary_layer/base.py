"""
Literary Layer — Base dataclasses
Single source of truth for all result types returned by the literary pipeline.

Phase 2 — LiteraryFinding, LiteraryResult  (rhetorical devices)
Phase 3 — WordFieldHit, WordFieldResult    (semantic field detection)
Phase 4 — NarrativeResult                  (voice, tense, syntax metrics)
Phase 7 — ArgumentationFinding, ArgumentationResult  (Ethos/Pathos/Logos)
Phase 8 — StylometricResult                (authorship fingerprint)
Phase 9 — LexicalProgressionResult         (MATTR curve, vocabulary richness)

Every finding that has a document location carries:
  • line_number  — 1-based line in the *original document* (not the window)
  • char_start   — absolute char offset into the original document
  • char_end     — absolute char offset into the original document
  • excerpt      — verbatim passage ≤ 140 chars, never split mid-word
so the researcher can jump straight to the source text rather than reading
abstract scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════
# Phase 2 — Rhetorical Devices
# ══════════════════════════════════════════════════════════

@dataclass
class LiteraryFinding:
    """
    One detected rhetorical device instance, fully localized to the source document.

    Attributes:
        device          — canonical device name ("alliteration", "simile", …)
        category        — "rhetorical" | "word_field" | "narrative"
        line_number     — 1-based line in the *original document* (not the window)
        char_start      — absolute char offset into the original document
        char_end        — absolute char offset into the original document
        excerpt         — verbatim passage ≤ 140 chars, never split mid-word
        matched_tokens  — the specific words that triggered the detection rule
        confidence      — 0.0 – 1.0 certainty score
        notes           — human-readable rule explanation shown as a UI tooltip
    """

    device:          str
    category:        str
    line_number:     int
    char_start:      int
    char_end:        int
    excerpt:         str
    matched_tokens:  List[str]
    confidence:      float
    notes:           str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device":         self.device,
            "category":       self.category,
            "line_number":    self.line_number,
            "char_start":     self.char_start,
            "char_end":       self.char_end,
            "excerpt":        self.excerpt,
            "matched_tokens": self.matched_tokens,
            "confidence":     round(self.confidence, 3),
            "notes":          self.notes,
        }


# ══════════════════════════════════════════════════════════
# Phase 3 — Word Fields
# ══════════════════════════════════════════════════════════

@dataclass
class WordFieldHit:
    """
    One token matched to a semantic domain field (e.g. NATURE, WAR, ANIMALS).
    Carries the token's location in the document so the researcher can inspect
    which specific words drive the field density score.

    Attributes:
        word        — surface form as it appears in the text
        lemma       — spaCy lemma (used for matching, shown for disambiguation)
        field       — canonical field name, e.g. "ANIMALS"
        similarity  — cosine similarity to the field centroid (0.0 – 1.0)
        line_number — 1-based line in the original document
        char_start  — absolute char offset of token start in original document
        char_end    — absolute char offset of token end in original document
    """

    word:        str
    lemma:       str
    field:       str
    similarity:  float
    line_number: int
    char_start:  int
    char_end:    int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word":        self.word,
            "lemma":       self.lemma,
            "field":       self.field,
            "similarity":  round(self.similarity, 3),
            "line_number": self.line_number,
            "char_start":  self.char_start,
            "char_end":    self.char_end,
        }


@dataclass
class WordFieldResult:
    """
    Aggregate word-field analysis for one analysis window.

    Attributes:
        field_density — {field_name: hits / total_content_words} for fields with ≥ 1 hit
        field_hits    — {field_name: [WordFieldHit, …]} for all active fields
    """

    field_density: Dict[str, float] = field(default_factory=dict)
    field_hits:    Dict[str, List[WordFieldHit]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_density": {k: round(v, 4) for k, v in self.field_density.items()},
            "field_hits": {
                f: [h.to_dict() for h in hits]
                for f, hits in self.field_hits.items()
            },
        }


# ══════════════════════════════════════════════════════════
# Phase 4 — Narrative Metrics
# ══════════════════════════════════════════════════════════

@dataclass
class NarrativeResult:
    """
    Aggregate narrative and stylistic metrics for one analysis window.

    Attributes:
        voice                 — pronoun distribution as ratios summing to 1.0
                                {first_person, second_person, third_person}
        tense                 — verb tense distribution as ratios summing to 1.0
                                {past, present, future}
        direct_speech_ratio   — proportion of window chars inside quotation marks
        mean_sentence_length  — average token count per sentence
        type_token_ratio      — MATTR (moving-average TTR, window=100 tokens)
        subordination_ratio   — subordinate-clause deps per sentence
        readability_score     — Flesch Reading Ease for EN (0-100+, higher = easier);
                                0.0 for languages without a calibrated formula
    """

    voice:                Dict[str, float]
    tense:                Dict[str, float]
    direct_speech_ratio:  float
    mean_sentence_length: float
    type_token_ratio:     float
    subordination_ratio:  float
    readability_score:    float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice": {k: round(v, 3) for k, v in self.voice.items()},
            "tense": {k: round(v, 3) for k, v in self.tense.items()},
            "direct_speech_ratio":  round(self.direct_speech_ratio,  3),
            "mean_sentence_length": round(self.mean_sentence_length, 1),
            "type_token_ratio":     round(self.type_token_ratio,     3),
            "subordination_ratio":  round(self.subordination_ratio,  3),
            "readability_score":    round(self.readability_score,    1),
        }


# ══════════════════════════════════════════════════════════
# Aggregate window result
# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
# Phase 7 — Argumentation Mining
# ══════════════════════════════════════════════════════════

@dataclass
class ArgumentationFinding:
    """
    One sentence classified by its rhetorical appeal type (Aristotle's triad)
    and its argumentative function.

    Attributes:
        appeal_type    — "logos" | "ethos" | "pathos"
        function       — "claim" | "premise" | "evidence" | "appeal"
        line_number    — 1-based line in the original document
        char_start     — absolute char offset of sentence start
        char_end       — absolute char offset of sentence end
        excerpt        — verbatim sentence (≤ 140 chars)
        trigger_words  — words that triggered the classification
        confidence     — 0.0 – 1.0 detection certainty
        notes          — human-readable explanation of the classification rule
    """

    appeal_type:   str
    function:      str
    line_number:   int
    char_start:    int
    char_end:      int
    excerpt:       str
    trigger_words: List[str]
    confidence:    float
    notes:         str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "appeal_type":  self.appeal_type,
            "function":     self.function,
            "line_number":  self.line_number,
            "char_start":   self.char_start,
            "char_end":     self.char_end,
            "excerpt":      self.excerpt,
            "trigger_words": self.trigger_words,
            "confidence":   round(self.confidence, 3),
            "notes":        self.notes,
        }


@dataclass
class ArgumentationResult:
    """
    Window-level argumentation profile: individual sentence findings plus
    the aggregate appeal ratios that characterise the passage as a whole.

    Attributes:
        findings        — per-sentence ArgumentationFinding objects
        ethos_ratio     — proportion of classified sentences that are ethos
        pathos_ratio    — proportion classified as pathos
        logos_ratio     — proportion classified as logos
        dominant_appeal — the appeal type with the highest ratio, or "balanced"
    """

    findings:        List[ArgumentationFinding] = field(default_factory=list)
    ethos_ratio:     float = 0.0
    pathos_ratio:    float = 0.0
    logos_ratio:     float = 0.0
    dominant_appeal: str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings":        [f.to_dict() for f in self.findings],
            "ethos_ratio":     round(self.ethos_ratio,  3),
            "pathos_ratio":    round(self.pathos_ratio, 3),
            "logos_ratio":     round(self.logos_ratio,  3),
            "dominant_appeal": self.dominant_appeal,
        }


# ══════════════════════════════════════════════════════════
# Phase 8 — Stylometric Fingerprinting
# ══════════════════════════════════════════════════════════

@dataclass
class StylometricResult:
    """
    Authorship fingerprint for one analysis window.

    Attributes:
        function_word_profile  — {word: occurrences per 1000 words} for top
                                 function words; the core of Burrows' Delta.
        punctuation_ratios     — {mark: occurrences per 1000 words}
        sentence_length_stats  — {mean, std, min, max, cv} (cv = std/mean)
        word_length_stats      — {mean, short_ratio ≤3, medium_ratio 4–6,
                                   long_ratio ≥7}
        hapax_ratio            — hapax legomena count / total unique word forms
        type_token_ratio       — raw TTR for the window (not MATTR)
    """

    function_word_profile: Dict[str, float] = field(default_factory=dict)
    punctuation_ratios:    Dict[str, float] = field(default_factory=dict)
    sentence_length_stats: Dict[str, float] = field(default_factory=dict)
    word_length_stats:     Dict[str, float] = field(default_factory=dict)
    hapax_ratio:           float = 0.0
    type_token_ratio:      float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_word_profile": {k: round(v, 3) for k, v in self.function_word_profile.items()},
            "punctuation_ratios":    {k: round(v, 3) for k, v in self.punctuation_ratios.items()},
            "sentence_length_stats": {k: round(v, 2) for k, v in self.sentence_length_stats.items()},
            "word_length_stats":     {k: round(v, 3) for k, v in self.word_length_stats.items()},
            "hapax_ratio":           round(self.hapax_ratio,      3),
            "type_token_ratio":      round(self.type_token_ratio, 3),
        }


# ══════════════════════════════════════════════════════════
# Phase 9 — Lexical Richness Progression
# ══════════════════════════════════════════════════════════

@dataclass
class LexicalProgressionResult:
    """
    Lexical richness waveform and vocabulary diagnostics for one analysis window.

    Attributes:
        mattr_curve         — list of 10 MATTR values sampled at evenly spaced
                              sub-windows, forming a richness waveform over the passage.
        mattr_trend         — "increasing" | "decreasing" | "stable"
                              (based on comparison of first-half vs last-half mean)
        hapax_ratio         — hapax legomena / total unique word forms
        vocab_growth_ratio  — actual unique types / Heaps'-law prediction
                              (ratio > 1 = richer than expected; < 1 = sparser)
        richness_label      — "rich" (MATTR > 0.75) | "moderate" (0.50–0.75)
                              | "sparse" (< 0.50)
        register_shift      — True if max(mattr_curve) − min(mattr_curve) > 0.25,
                              signalling a vocabulary / register change mid-window
    """

    mattr_curve:        List[float] = field(default_factory=list)
    mattr_trend:        str   = ""
    hapax_ratio:        float = 0.0
    vocab_growth_ratio: float = 0.0
    richness_label:     str   = ""
    register_shift:     bool  = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mattr_curve":        [round(v, 3) for v in self.mattr_curve],
            "mattr_trend":        self.mattr_trend,
            "hapax_ratio":        round(self.hapax_ratio,        3),
            "vocab_growth_ratio": round(self.vocab_growth_ratio, 3),
            "richness_label":     self.richness_label,
            "register_shift":     self.register_shift,
        }


# ══════════════════════════════════════════════════════════
# Aggregate window result
# ══════════════════════════════════════════════════════════

@dataclass
class LiteraryResult:
    """
    All literary findings for one analysis window.

    Phase 2  — rhetorical_findings populated.
    Phase 3  — word_fields populated.
    Phase 4  — narrative populated.
    Phase 7  — argumentation populated.
    Phase 8  — stylometry populated.
    Phase 9  — lexical_progression populated.
    """

    rhetorical_findings: List[LiteraryFinding]           = field(default_factory=list)
    word_fields:         Optional[WordFieldResult]        = None
    narrative:           Optional[NarrativeResult]        = None
    argumentation:       Optional[ArgumentationResult]    = None
    stylometry:          Optional[StylometricResult]      = None
    lexical_progression: Optional[LexicalProgressionResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rhetorical_findings": [f.to_dict() for f in self.rhetorical_findings],
            "word_fields":         self.word_fields.to_dict()         if self.word_fields         else None,
            "narrative":           self.narrative.to_dict()           if self.narrative           else None,
            "argumentation":       self.argumentation.to_dict()       if self.argumentation       else None,
            "stylometry":          self.stylometry.to_dict()          if self.stylometry          else None,
            "lexical_progression": self.lexical_progression.to_dict() if self.lexical_progression else None,
        }
