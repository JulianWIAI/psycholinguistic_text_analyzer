"""
MODULE 3 — Macro-Layer: Semantics & Vocabulary
Analyzes words to extract the conscious framing of the author.

Uses spaCy for lemmatization, then maps lemmas to 4 semantic clusters:
    1. Resources  — Scarcity vs. Abundance
    2. Power      — Control vs. Submission
    3. Visibility — Concealment vs. Exposure
    4. Temporal   — Past/Nostalgic vs. Future/Projective

Score per cluster per window = Σ(word_weight × frequency) / total_words_in_window
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import spacy

# ---------------------------------------------------------------------------
# Semantic Cluster Dictionaries
# Each word maps to: (cluster_name, pole_name, weight)
# ---------------------------------------------------------------------------

_CLUSTER_DEFINITIONS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "tight", "strict", "budget", "limit", "scarce", "lack",
            "shortage", "constrain", "deplete", "minimal", "sparse",
        ],
        "abundance": [
            "flow", "massive", "endless", "plenty", "surplus", "rich",
            "overflow", "generous", "ample", "plentiful", "wealth",
        ],
    },
    "power": {
        "control": [
            "manage", "enforce", "dictate", "command", "dominate",
            "control", "direct", "govern", "rule", "authority", "mandate",
        ],
        "submission": [
            "undergo", "assign", "force", "comply", "submit", "yield",
            "obey", "subordinate", "defer", "accept", "endure",
        ],
    },
    "visibility": {
        "concealment": [
            "layer", "obscure", "shadow", "hide", "conceal", "mask",
            "cover", "veil", "bury", "suppress", "muffle",
        ],
        "exposure": [
            "bright", "obvious", "clear", "reveal", "expose", "transparent",
            "open", "visible", "illuminate", "manifest", "display",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "return", "memory", "root", "tradition", "past", "former",
            "restore", "remember", "recall", "heritage", "origin",
        ],
        "future_projective": [
            "advance", "horizon", "next", "future", "forward", "progress",
            "innovate", "envision", "emerge", "prospect", "vision",
        ],
    },
}

# Flat lookup: lemma -> (cluster, pole, weight=1.0)
_WORD_LOOKUP: Dict[str, tuple] = {}
for _cluster, _poles in _CLUSTER_DEFINITIONS.items():
    for _pole, _words in _poles.items():
        for _w in _words:
            _WORD_LOOKUP[_w] = (_cluster, _pole, 1.0)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ClusterHit:
    lemma: str
    cluster: str
    pole: str
    weight: float


@dataclass
class MacroScore:
    """
    cluster_scores: {cluster_name: {pole_name: normalized_score}}
    Scores are normalized by total_words in the window.
    """
    cluster_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    total_words: int = 0
    hits: List[ClusterHit] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class SemanticAnalyzer:
    """
    Lemmatizes text with spaCy and scores windows against semantic clusters.
    Load once; reuse across all windows.
    """

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        try:
            self._nlp = spacy.load(spacy_model)
        except OSError:
            raise RuntimeError(
                f"spaCy model '{spacy_model}' not found. "
                f"Install it with: python -m spacy download {spacy_model}"
            )

    def analyze(self, text: str) -> MacroScore:
        """
        Lemmatize *text* and compute cluster scores.
        Stop-words and punctuation are excluded from token count.
        """
        doc = self._nlp(text)

        # Keep only alphabetic, non-stop tokens for scoring
        content_tokens = [
            t for t in doc if t.is_alpha and not t.is_stop
        ]
        total_words = len(content_tokens)

        # Accumulate raw weighted hits per cluster/pole
        raw: Dict[str, Dict[str, float]] = {
            cluster: {pole: 0.0 for pole in poles}
            for cluster, poles in _CLUSTER_DEFINITIONS.items()
        }
        hits: List[ClusterHit] = []

        for token in content_tokens:
            lemma = token.lemma_.lower()
            if lemma in _WORD_LOOKUP:
                cluster, pole, weight = _WORD_LOOKUP[lemma]
                raw[cluster][pole] += weight
                hits.append(ClusterHit(lemma=lemma, cluster=cluster, pole=pole, weight=weight))

        # Normalize: score = Σ(weight × freq) / total_words
        normalized: Dict[str, Dict[str, float]] = {}
        for cluster, poles in raw.items():
            normalized[cluster] = {
                pole: (score / total_words if total_words > 0 else 0.0)
                for pole, score in poles.items()
            }

        return MacroScore(
            cluster_scores=normalized,
            total_words=total_words,
            hits=hits,
        )
