"""
Multilingual Semantic Analyzer
Generic semantic analyzer for non-English Latin-script languages (ES, FR).

Mirrors the interface of SemanticAnalyzer but accepts an arbitrary cluster
dictionary and any spaCy model — making it reusable for every Latin-script
language expansion without code duplication.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from macro_layer.semantic_analyzer import MacroScore, ClusterHit


class MultilingualSemanticAnalyzer:
    """
    Drop-in replacement for SemanticAnalyzer for non-English languages.

    Parameters
    ----------
    spacy_model   : spaCy model identifier string (e.g. "es_core_news_sm")
    clusters      : cluster definition dict matching the structure in es/fr_clusters.py
    """

    def __init__(self, spacy_model: str, clusters: Dict[str, Dict[str, List[str]]]):
        from language.registry import ModelRegistry
        self._nlp      = ModelRegistry.load(spacy_model)
        self._clusters = clusters
        self._lookup   = self._build_lookup(clusters)

    # ------------------------------------------------------------------
    # Public interface — same as SemanticAnalyzer
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> MacroScore:
        doc = self._nlp(text)

        content_tokens = [t for t in doc if t.is_alpha and not t.is_stop]
        total_words = max(1, len(content_tokens))

        raw: Dict[str, Dict[str, float]] = {
            cluster: {pole: 0.0 for pole in poles}
            for cluster, poles in self._clusters.items()
        }
        hits: List[ClusterHit] = []

        for token in content_tokens:
            lemma = token.lemma_.lower()
            if lemma in self._lookup:
                cluster, pole, weight = self._lookup[lemma]
                raw[cluster][pole] += weight
                hits.append(ClusterHit(lemma=lemma, cluster=cluster, pole=pole, weight=weight))

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
