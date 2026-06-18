"""
MODULE 3 — Macro-Layer: Semantics & Vocabulary
Analyzes words to extract the conscious framing of the author.

Uses spaCy for lemmatization, then maps lemmas to 6 semantic clusters:
    1. Resources  — Scarcity vs. Abundance
    2. Power      — Control vs. Submission
    3. Visibility — Concealment vs. Exposure
    4. Temporal   — Past/Nostalgic vs. Future/Projective
    5. Cognitive  — Scientific/Empirical vs. Emotional/Abstract
    6. Kinetic    — Aggression/Strike vs. Diplomacy/Stasis

Score per cluster per window = Σ(similarity_weight) / total_words_in_window
Vector similarity (cosine > 0.65) used when _md model is loaded;
falls back to exact lemma match when only _sm is available.
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import spacy


# ---------------------------------------------------------------------------
# Model loader with _md → _sm graceful fallback
# ---------------------------------------------------------------------------

def _load_spacy(model: str) -> spacy.Language:
    """Load a spaCy model; fall back from _md to _sm with a RuntimeWarning."""
    try:
        return spacy.load(model)
    except OSError:
        sm = model.replace("_md", "_sm").replace("_lg", "_sm")
        warnings.warn(
            f"Vector model '{model}' not found — falling back to '{sm}' "
            f"(no word vectors; exact-match scoring only). "
            f"For vector similarity install: python -m spacy download {model}",
            RuntimeWarning,
            stacklevel=2,
        )
        try:
            return spacy.load(sm)
        except OSError:
            raise RuntimeError(
                f"spaCy model '{sm}' not found. "
                f"Install it with: python -m spacy download {sm}"
            )


# ---------------------------------------------------------------------------
# Semantic Cluster Dictionaries  (English / lemma forms)
# ---------------------------------------------------------------------------

_CLUSTER_DEFINITIONS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "ration", "deficit", "starvation", "strict", "squeeze",
            "tight", "scarce", "shortage", "deplete", "limit",
            "constrain", "austerity", "drain", "withhold", "cutback",
            "sparse", "dearth", "minimal", "exhaust", "deprivation",
            "cap", "freeze", "lack", "budget", "scant",
        ],
        "abundance": [
            "surplus", "flood", "lavish", "endless", "asset",
            "wealth", "overflow", "generous", "ample", "plentiful",
            "rich", "bounty", "profuse", "bountiful", "stockpile",
            "excess", "windfall", "glut", "cascade", "expansive",
            "teem", "abundant", "saturate", "massive", "flow",
        ],
    },
    "power": {
        "control": [
            "enforce", "dictate", "authorize", "grid", "deploy",
            "command", "dominate", "govern", "mandate", "surveillance",
            "coerce", "compel", "monitor", "regulate", "override",
            "contain", "leverage", "manage", "direct", "rule",
            "suppress", "execute", "channel", "lock", "control",
        ],
        "submission": [
            "endure", "assign", "force", "sweep", "yield",
            "comply", "submit", "obey", "subordinate", "defer",
            "accept", "capitulate", "surrender", "tolerate", "succumb",
            "resign", "confine", "trap", "pressure", "helpless",
            "bear", "absorb", "acquiesce", "relent", "subject",
        ],
    },
    "visibility": {
        "concealment": [
            "obscure", "intercept", "veil", "encrypt", "shadow",
            "layer", "hide", "conceal", "mask", "cover",
            "bury", "suppress", "cloak", "shroud", "camouflage",
            "screen", "filter", "divert", "redirect", "blind",
            "occlude", "muffle", "dark", "embed", "invisible",
        ],
        "exposure": [
            "broadcast", "clear", "obvious", "surface", "bright",
            "reveal", "expose", "transparent", "open", "visible",
            "illuminate", "manifest", "display", "signal", "publish",
            "overt", "unmask", "flag", "declare", "naked",
            "explicit", "bare", "disclose", "direct", "raw",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "roots", "restore", "memory", "before", "legacy",
            "return", "tradition", "former", "remember", "recall",
            "heritage", "origin", "establish", "relic", "nostalgia",
            "reclaim", "ancestor", "revert", "prior", "remnant",
            "archive", "bygone", "dated", "historic", "founding",
        ],
        "future_projective": [
            "horizon", "incoming", "advance", "threat", "trajectory",
            "progress", "innovate", "emerge", "vision", "target",
            "escalate", "imminent", "deploy", "project", "upcoming",
            "surge", "converge", "loom", "gather", "onset",
            "forecast", "impend", "next", "forward", "mobilize",
        ],
    },
    "cognitive": {
        "scientific": [
            "calculate", "variable", "physics", "metric", "observe",
            "structure", "analyze", "empirical", "parameter", "measure",
            "quantify", "model", "data", "hypothesis", "systematic",
            "logic", "formula", "experiment", "evidence", "verify",
            "calibrate", "classify", "precision", "algorithm", "derive",
        ],
        "emotional": [
            "feel", "hope", "soul", "despair", "intuitive",
            "abstract", "sense", "believe", "dream", "suffer",
            "grieve", "love", "fear", "ache", "yearn",
            "mourn", "long", "anguish", "imagine", "crave",
            "empathize", "sorrow", "passion", "wish", "heartfelt",
        ],
    },
    "kinetic": {
        "aggression": [
            "strike", "breach", "kinetic", "eliminate", "target",
            "attack", "assault", "destroy", "neutralize", "rupture",
            "penetrate", "crush", "overwhelm", "raid", "detonate",
            "mobilize", "launch", "engage", "escalate", "annihilate",
            "obliterate", "seize", "capture", "hit", "breach",
        ],
        "diplomacy": [
            "negotiate", "hold", "stall", "treaty", "balance",
            "ceasefire", "dialogue", "mediate", "stabilize", "pause",
            "defer", "reconcile", "compromise", "withdraw", "restrain",
            "moderate", "concede", "settle", "agree", "resolve",
            "sustain", "maintain", "observe", "contain", "monitor",
        ],
    },
}

# Flat lookup: lemma -> (cluster, pole, weight=1.0) — used as exact-match fallback
_WORD_LOOKUP: Dict[str, Tuple[str, str, float]] = {}
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
# VectorClusterScorer
# ---------------------------------------------------------------------------

_SIMILARITY_THRESHOLD = 0.65


class VectorClusterScorer:
    """
    Pre-computes L2-normalized centroid vectors from 25 seed words per pole,
    then scores window tokens via batched cosine similarity:
        (n_tokens, dim) @ (dim, n_poles) → (n_tokens, n_poles)

    Falls back to exact lemma-match when the model has no word vectors (_sm).
    """

    def __init__(
        self,
        nlp: spacy.Language,
        clusters: Dict[str, Dict[str, List[str]]],
        exact_lookup: Optional[Dict[str, Tuple[str, str, float]]] = None,
    ):
        self._nlp = nlp
        self._clusters = clusters
        self._exact_lookup = exact_lookup or {}
        self._has_vectors: bool = nlp.vocab.vectors.shape[0] > 0
        self._pole_order: List[Tuple[str, str]] = []
        self._centroids: Optional[np.ndarray] = None

        if self._has_vectors:
            self._build_centroids()

    @property
    def has_vectors(self) -> bool:
        return self._has_vectors

    def _build_centroids(self) -> None:
        dim = self._nlp.vocab.vectors_length
        pole_order: List[Tuple[str, str]] = []
        centroid_list: List[np.ndarray] = []

        for cluster, poles in self._clusters.items():
            for pole, seed_words in poles.items():
                pole_order.append((cluster, pole))
                docs = list(self._nlp.pipe(seed_words))
                vecs = [
                    doc[0].vector
                    for doc in docs
                    if doc and len(doc) > 0 and doc[0].has_vector
                ]
                if vecs:
                    c = np.mean(vecs, axis=0).astype(np.float32)
                    norm = np.linalg.norm(c)
                    if norm > 0:
                        c /= norm
                else:
                    c = np.zeros(dim, dtype=np.float32)
                centroid_list.append(c)

        self._pole_order = pole_order
        # Shape: (dim, n_poles) — ready for right-multiply with token matrix
        self._centroids = np.stack(centroid_list, axis=1).astype(np.float32)

    def score_tokens(
        self,
        content_tokens,
    ) -> Tuple[Dict[str, Dict[str, float]], List[ClusterHit]]:
        """Score content tokens; returns (raw_cluster_dict, hits_list)."""
        raw: Dict[str, Dict[str, float]] = {
            cluster: {pole: 0.0 for pole in poles}
            for cluster, poles in self._clusters.items()
        }
        hits: List[ClusterHit] = []

        if self._has_vectors and self._centroids is not None:
            self._score_vector(content_tokens, raw, hits)
        else:
            self._score_exact(content_tokens, raw, hits)

        return raw, hits

    def _score_vector(self, tokens, raw: dict, hits: list) -> None:
        valid = [(t, t.vector) for t in tokens if t.has_vector]
        if not valid:
            return

        token_objs, vecs = zip(*valid)
        mat = np.array(vecs, dtype=np.float32)           # (n_tokens, dim)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        mat /= np.where(norms > 0, norms, 1.0)

        sim = mat @ self._centroids                       # (n_tokens, n_poles)

        for tok_idx, token in enumerate(token_objs):
            for pole_idx, (cluster, pole) in enumerate(self._pole_order):
                s = float(sim[tok_idx, pole_idx])
                if s > _SIMILARITY_THRESHOLD:
                    raw[cluster][pole] += s
                    hits.append(ClusterHit(
                        lemma=token.lemma_.lower(),
                        cluster=cluster,
                        pole=pole,
                        weight=round(s, 4),
                    ))

    def _score_exact(self, tokens, raw: dict, hits: list) -> None:
        for token in tokens:
            lemma = token.lemma_.lower()
            if lemma in self._exact_lookup:
                cluster, pole, weight = self._exact_lookup[lemma]
                raw[cluster][pole] += weight
                hits.append(ClusterHit(lemma=lemma, cluster=cluster, pole=pole, weight=weight))


# ---------------------------------------------------------------------------
# English Semantic Analyzer
# ---------------------------------------------------------------------------

class SemanticAnalyzer:
    """
    Lemmatizes text with spaCy and scores windows against semantic clusters.
    Attempts to load en_core_web_md (vectors); falls back to en_core_web_sm.
    Load once; reuse across all windows.
    """

    def __init__(self, spacy_model: str = "en_core_web_md"):
        self._nlp = _load_spacy(spacy_model)
        self._scorer = VectorClusterScorer(
            nlp=self._nlp,
            clusters=_CLUSTER_DEFINITIONS,
            exact_lookup=_WORD_LOOKUP,
        )

    def analyze(self, text: str) -> MacroScore:
        """
        Lemmatize *text* and compute cluster scores.
        Stop-words and punctuation are excluded from token count.
        """
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
