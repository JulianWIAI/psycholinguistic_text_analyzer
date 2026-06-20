"""
Multilingual Semantic Analyzer
Generic semantic analyzer for non-English Latin-script languages (DE, ES, FR).

Mirrors the interface of SemanticAnalyzer but accepts an arbitrary cluster
dictionary and any spaCy model — making it reusable for every Latin-script
language expansion without code duplication.

Uses VectorClusterScorer (cosine similarity against pole centroids) when an
_md model is available; falls back to exact lemma-match with _sm.
"""

import re
import warnings
from typing import Dict, List, Tuple

from macro_layer.semantic_analyzer import (
    MacroScore,
    ClusterHit,
    VectorClusterScorer,
    _load_spacy,
    extract_entity_polarity,
    apply_pos_fallback,
)

# Arabic harakat diacritics (U+064B–U+065F) and superscript alef (U+0670)
_RE_DIACRITICS = re.compile(r"[ً-ٰٟ]")
# Farsi zero-width non-joiner used in compound words (e.g. بی‌منابع)
_ZWNJ = "‌"


# Arabic/Farsi clitics that attach to the start of words in running text.
# Ordered longest-first so the stripping probe tries "وال" before "و".
_AR_PREFIXES = ("وال", "فال", "بال", "لل", "و", "ف", "ب", "ل", "ال")


class MultilingualSemanticAnalyzer:
    """
    Drop-in replacement for SemanticAnalyzer for non-English languages.

    Parameters
    ----------
    spacy_model   : spaCy model identifier string (e.g. "de_core_news_md")
    clusters      : cluster definition dict matching the structure in *_clusters.py
    """

    def __init__(self, spacy_model: str, clusters: Dict[str, Dict[str, List[str]]]):
        self._nlp = _load_spacy(spacy_model)

        # xx_ent_wiki_sm (used for AR/FA) ships with only an NER component —
        # no parser or senter.  extract_entity_polarity accesses ent.sent which
        # requires sentence boundaries, so inject a sentencizer when none exists.
        _SENT_COMPONENTS = ("parser", "senter", "sentencizer")
        if not any(self._nlp.has_pipe(p) for p in _SENT_COMPONENTS):
            self._nlp.add_pipe("sentencizer")

        # Task 3 — cluster loading verification: warn if any pole is under-seeded.
        for cluster, poles in clusters.items():
            for pole, words in poles.items():
                if len(words) < 5:
                    warnings.warn(
                        f"[{spacy_model}] cluster '{cluster}/{pole}' has only "
                        f"{len(words)} seed word(s) — cosine similarity requires "
                        "≥ 5 for reliable centroids.",
                        RuntimeWarning,
                        stacklevel=2,
                    )

        self._clusters = clusters
        self._lookup = self._build_lookup(clusters)
        self._scorer = VectorClusterScorer(
            nlp=self._nlp,
            clusters=clusters,
            exact_lookup=self._lookup,
        )

    # ------------------------------------------------------------------
    # Public interface — same as SemanticAnalyzer
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> MacroScore:
        doc = self._nlp(text)
        content_tokens = [t for t in doc if t.is_alpha and not t.is_stop]
        total_words = max(1, len(content_tokens))

        raw, hits = self._scorer.score_tokens(content_tokens)

        # Task 1 — absolute POS fallback for short / vocabulary-sparse intercepts.
        # Fires when every cluster score is zero (no similarity or exact-match hit).
        # Guarantees the UI Driver Matrix is populated regardless of text length.
        if not hits:
            extra_raw, hits = apply_pos_fallback(doc, self._lookup)
            for cluster, poles in extra_raw.items():
                for pole, score in poles.items():
                    raw.setdefault(cluster, {})[pole] = (
                        raw.get(cluster, {}).get(pole, 0.0) + score
                    )

        normalized: Dict[str, Dict[str, float]] = {
            cluster: {
                pole: score / total_words
                for pole, score in poles.items()
            }
            for cluster, poles in raw.items()
        }

        entity_polarity_map = extract_entity_polarity(doc, self._scorer)

        return MacroScore(
            cluster_scores=normalized,
            total_words=total_words,
            hits=hits,
            entity_polarity_map=entity_polarity_map,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_lookup(
        clusters: Dict[str, Dict[str, List[str]]]
    ) -> Dict[str, Tuple[str, str, float]]:
        """
        Build the exact-match lemma → (cluster, pole, weight) index.

        For Arabic/Farsi seed words, also register diacritic-stripped and
        ZWNJ-stripped variants so that harakat-annotated input tokens and
        Farsi compound words separated by U+200C still match.
        """
        lookup: Dict[str, Tuple[str, str, float]] = {}
        for cluster, poles in clusters.items():
            for pole, words in poles.items():
                for w in words:
                    key = w.lower()
                    lookup[key] = (cluster, pole, 1.0)

                    # Arabic harakat diacritics (حركات) — strip from key
                    stripped = _RE_DIACRITICS.sub("", key)
                    if stripped != key:
                        lookup.setdefault(stripped, (cluster, pole, 1.0))

                    # Farsi ZWNJ compound words (e.g. بی‌منابع → بیمنابع)
                    no_zwnj = key.replace(_ZWNJ, "")
                    if no_zwnj != key:
                        lookup.setdefault(no_zwnj, (cluster, pole, 1.0))

                    # Arabic/Farsi: xx_ent_wiki_sm does not split clitics from the
                    # following word — register the most common prefix-attached forms
                    # so "وهجوم" (and+attack) matches the seed word "هجوم".
                    for pfx in _AR_PREFIXES:
                        lookup.setdefault(pfx + key, (cluster, pole, 1.0))
        return lookup
