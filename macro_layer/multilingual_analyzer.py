"""
Multilingual Semantic Analyzer
Generic semantic analyzer for non-English Latin-script languages (DE, ES, FR).

Mirrors the interface of SemanticAnalyzer but accepts an arbitrary cluster
dictionary and any spaCy model — making it reusable for every Latin-script
language expansion without code duplication.

Uses VectorClusterScorer (cosine similarity against pole centroids) when an
_md model is available; falls back to exact lemma-match with _sm.
"""

from typing import Dict, List, Tuple

from macro_layer.semantic_analyzer import (
    MacroScore,
    ClusterHit,
    VectorClusterScorer,
    _load_spacy,
)


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

        normalized: Dict[str, Dict[str, float]] = {
            cluster: {
                pole: score / total_words
                for pole, score in poles.items()
            }
            for cluster, poles in raw.items()
        }

        return MacroScore(cluster_scores=normalized, total_words=total_words, hits=hits)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_lookup(
        clusters: Dict[str, Dict[str, List[str]]]
    ) -> Dict[str, Tuple[str, str, float]]:
        lookup: Dict[str, Tuple[str, str, float]] = {}
        for cluster, poles in clusters.items():
            for pole, words in poles.items():
                for w in words:
                    lookup[w.lower()] = (cluster, pole, 1.0)
        return lookup
