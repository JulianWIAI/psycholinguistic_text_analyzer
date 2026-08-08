"""
Literary Layer — Semantic Field Scorer (Phase 3)
Assigns content words in a spaCy Doc to thematic domain fields (ANIMALS,
NATURE, WAR, LOVE, etc.) using cosine vector similarity against pre-computed
field centroids.

Architecture mirrors the existing VectorClusterScorer in macro_layer/semantic_analyzer.py:
    1. Build a centroid vector for each field by averaging the spaCy vocabulary
       vectors of its seed words.
    2. For each non-stop content token with a vector, compute cosine similarity
       to every centroid.
    3. Assign the token to any field whose centroid similarity exceeds
       SIMILARITY_THRESHOLD.

Centroid computation is cached per language after the first call so it runs
only once per server lifetime, not once per window.

Requirements:
    The active spaCy model must have word vectors (i.e. *_md or *_lg variant).
    If no vectors are available, score() returns an empty WordFieldResult
    without raising — the caller receives silently empty word-field data.

Supported languages (Phase 3): EN, DE, FR.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from literary_layer.base import WordFieldHit, WordFieldResult
from literary_layer.line_index import char_to_line
from literary_layer.word_fields.en_fields import EN_FIELDS
from literary_layer.word_fields.de_fields import DE_FIELDS
from literary_layer.word_fields.fr_fields import FR_FIELDS

# Minimum cosine similarity for a token to be assigned to a field.
# Consistent with the macro layer's cluster-scoring threshold (0.65) but
# slightly lower here to capture field-adjacent vocabulary
# (e.g. "saddle" is closely related to ANIMALS even without being an animal word).
SIMILARITY_THRESHOLD: float = 0.60

# Content tokens shorter than this are unlikely to carry field-specific meaning
MIN_TOKEN_LENGTH: int = 3

# POS tags excluded from field scoring — pure function words with no semantic
# domain that would generate noise in the centroid comparisons.
SKIP_POS: frozenset = frozenset({
    "DET", "ADP", "CCONJ", "SCONJ", "PART", "PUNCT", "SPACE", "NUM",
})

# Map language codes to their seed dictionaries
_SEED_REGISTRY: Dict[str, Dict[str, List[str]]] = {
    "EN": EN_FIELDS,
    "DE": DE_FIELDS,
    "FR": FR_FIELDS,
}


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """
    Return the cosine similarity between two L2-normalised vectors.
    Both *a* and *b* are expected to be pre-normalised, so this is just a dot product.
    Returns 0.0 if either vector is the zero vector.
    """
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class FieldScorer:
    """
    Computes per-token semantic field similarity and aggregates results into a
    WordFieldResult for one analysis window.

    The centroid cache (_cache) stores L2-normalised centroid vectors per language.
    They are computed lazily on the first call for each language and reused for
    all subsequent calls — safe because the spaCy model is a fixed singleton.
    """

    def __init__(self) -> None:
        # {language_code: {field_name: np.ndarray (L2-normalised centroid)}}
        self._cache: Dict[str, Dict[str, np.ndarray]] = {}

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_centroids(
        self,
        doc,
        language: str,
    ) -> Dict[str, np.ndarray]:
        """
        Compute and cache L2-normalised centroid vectors for all fields in *language*.

        Uses the spaCy vocabulary attached to *doc* to look up word vectors for
        each seed word.  Seeds without vectors are silently skipped.
        Caches results so computation runs only once per language per server start.

        Returns an empty dict if no seed in any field has a vector (i.e. the model
        has no word vectors at all — typically the *_sm fallback).
        """
        if language in self._cache:
            return self._cache[language]

        seeds = _SEED_REGISTRY.get(language, {})
        if not seeds:
            self._cache[language] = {}
            return {}

        centroids: Dict[str, np.ndarray] = {}
        for field_name, words in seeds.items():
            # Collect vectors for seed words that exist in the model vocabulary
            vecs = [
                doc.vocab[w].vector
                for w in words
                if doc.vocab[w].has_vector
            ]
            if not vecs:
                continue   # field has no coverage in this model — skip silently

            centroid = np.mean(vecs, axis=0).astype(np.float32)
            # L2-normalise so cosine reduces to a dot product in _cosine()
            norm = float(np.linalg.norm(centroid))
            if norm > 0:
                centroid = centroid / norm

            centroids[field_name] = centroid

        self._cache[language] = centroids
        return centroids

    # ── Public API ─────────────────────────────────────────────────────────────

    def score(
        self,
        doc,
        start_char: int,
        line_index: List[int],
        language: str,
    ) -> WordFieldResult:
        """
        Score every content token in *doc* against all semantic field centroids
        for *language* and return a WordFieldResult with per-field hit lists and
        density ratios.

        Args:
            doc:         spaCy Doc (pre-parsed by the macro analyzer).
            start_char:  Absolute char offset of the window start in the full
                         document — used to produce document-level positions for hits.
            line_index:  Pre-built char-to-line map from build_line_index().
            language:    ISO language code ("EN", "DE", "FR").

        Returns:
            WordFieldResult with fields populated.  Empty if the model has no
            vectors or the language has no seed dictionary.
        """
        centroids = self._build_centroids(doc, language)
        if not centroids:
            # Model has no vectors (e.g. _sm fallback) — return empty result
            return WordFieldResult()

        hits_by_field: Dict[str, List[WordFieldHit]] = {f: [] for f in centroids}
        content_token_count = 0

        for token in doc:
            # Skip tokens that are not meaningful content
            if (
                not token.is_alpha
                or token.is_stop
                or token.pos_ in SKIP_POS
                or len(token.text) < MIN_TOKEN_LENGTH
                or not token.has_vector
            ):
                continue

            content_token_count += 1
            tok_vec = token.vector

            # Compute absolute position for this token in the original document
            abs_start = start_char + token.idx
            abs_end   = abs_start + len(token.text)
            line_num  = char_to_line(abs_start, line_index)

            # Score against every field centroid
            for field_name, centroid in centroids.items():
                sim = _cosine(tok_vec, centroid)
                if sim >= SIMILARITY_THRESHOLD:
                    hits_by_field[field_name].append(WordFieldHit(
                        word=token.text,
                        lemma=token.lemma_,
                        field=field_name,
                        similarity=float(sim),
                        line_number=line_num,
                        char_start=abs_start,
                        char_end=abs_end,
                    ))

        # Compute density as hits / content_token_count for fields with at least 1 hit
        total = max(1, content_token_count)
        field_density: Dict[str, float] = {
            f: len(hits) / total
            for f, hits in hits_by_field.items()
            if hits
        }
        active_hits: Dict[str, List[WordFieldHit]] = {
            f: hits
            for f, hits in hits_by_field.items()
            if hits
        }

        return WordFieldResult(field_density=field_density, field_hits=active_hits)
