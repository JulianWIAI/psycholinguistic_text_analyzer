"""
Lexical Affinity Radar — Graphemic Iconicity Module (v1.0)

Analyzes the geometric-psychological profile of a text via the initial
letters of its content words (nouns, verbs, adjectives, proper nouns).

Based on The Geometric Lexicon & Psychological Profiling white paper v3.0.
The 26 Latin letters are organized into 7 geometric clusters that correspond
to distinct psychological and environmental states for both the author and
the reader.

Only valid for Latin-script languages (EN, DE, ES, FR). Caller is responsible
for gating by language code.
"""

from typing import Any, Dict

# ---------------------------------------------------------------------------
# 7-cluster letter mapping
# ---------------------------------------------------------------------------

_CLUSTERS: Dict[str, frozenset] = {
    "structural":  frozenset("BDHOU"),   # containment, stability, building
    "kinetic":     frozenset("KXZQ"),    # disruption, collision, rapid change
    "fluid":       frozenset("CJS"),     # adaptability, flow, evasion
    "expansive":   frozenset("MW"),      # scale, mass, global scope
    "directional": frozenset("AFPTY"),   # ambition, hierarchy, planning
    "orthogonal":  frozenset("EIL"),     # logic, order, systematic structure
    "complex":     frozenset("GNRV"),    # tension, primal action, binding forces
}

# Reverse lookup: uppercase letter → cluster name
_LETTER_TO_CLUSTER: Dict[str, str] = {
    letter: cluster
    for cluster, letters in _CLUSTERS.items()
    for letter in letters
}

# POS tags considered content words
_CONTENT_POS = frozenset({"NOUN", "VERB", "ADJ", "PROPN"})

# ---------------------------------------------------------------------------
# Profile text tables
# ---------------------------------------------------------------------------

_AUTHOR_REALITY: Dict[str, str] = {
    "structural":  (
        "Anchored in security, stasis, and building. "
        "Operates within well-defined, protected boundaries."
    ),
    "kinetic":     (
        "Surrounded by conflict, erratic energy, or rapid change. "
        "Current environment is highly volatile and action-oriented."
    ),
    "fluid":       (
        "Highly adaptable and evasive. Navigating shifting, fluid "
        "environments that resist rigid commitment."
    ),
    "expansive":   (
        "Dealing with heavy burdens or large-scale, global concepts. "
        "Daily scope is physically or mentally massive."
    ),
    "directional": (
        "Goal-oriented and strictly planned. Operating in hierarchies; "
        "cognitive ambition dominates over physical grounding."
    ),
    "orthogonal":  (
        "Highly logical and systematic. Environment demands strict "
        "boundaries, internal logic, and ubiquitous observation."
    ),
    "complex":     (
        "Navigating complex relationships and binding forces. "
        "Balancing primal actions with deep internal or external tension."
    ),
}

_READER_DEFICIT: Dict[str, str] = {
    "structural":  (
        "Experiencing environmental volatility. "
        "Audience craves safety, containment, and a psychological anchor."
    ),
    "kinetic":     (
        "Feeling stagnant or bored. Audience craves stimulation, "
        "collision, and the disruption of a monotonous life."
    ),
    "fluid":       (
        "Feeling trapped by rigid rules or physical constraints. "
        "Audience craves flexibility and smooth evasion."
    ),
    "expansive":   (
        "Feeling insignificant or isolated. Audience desires to be part "
        "of something monumental or globally significant."
    ),
    "directional": (
        "Lacking direction or clear leadership. Audience seeks a defined "
        "path forward and authoritative cognitive guidance."
    ),
    "orthogonal":  (
        "Overwhelmed by chaos or ambiguity. Audience craves order, "
        "extreme clarity, and rational systematic logic."
    ),
    "complex":     (
        "Feeling disconnected or unresolved. Audience desires deep binding "
        "connection or resolution of internal tension vectors."
    ),
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class LexicalAffinityRadar:
    """
    Parameters
    ----------
    spacy_doc
        A processed spaCy Doc with POS tags and stop-word flags.
    macro_cluster_scores : dict, optional
        Nested {cluster: {pole: score}} from the macro semantic analyzer.
        Used only for the is_posturing cross-reference check.
    """

    def __init__(self, spacy_doc, macro_cluster_scores: Dict[str, Dict[str, float]] = None):
        self._doc    = spacy_doc
        self._macro  = macro_cluster_scores or {}

    # ------------------------------------------------------------------
    def analyze(self) -> Dict[str, Any]:
        """
        Return the full lexical affinity payload::

            {
                "clusters":            {"structural": 34.2, "kinetic": 8.1, ...},
                "dominant":            "structural",
                "total_content_words": 47,
                "author_reality":      "...",
                "reader_deficit":      "...",
                "is_posturing":        false,
            }
        """
        counts: Dict[str, int] = {c: 0 for c in _CLUSTERS}
        total = 0

        for token in self._doc:
            if token.is_stop:
                continue
            if token.pos_ not in _CONTENT_POS:
                continue
            surface = token.text.strip()
            if not surface:
                continue
            first = surface[0].upper()
            cluster = _LETTER_TO_CLUSTER.get(first)
            if cluster is None:
                continue  # digit, punctuation, or non-Latin initial
            counts[cluster] += 1
            total += 1

        if total == 0:
            percentages = {c: 0.0 for c in _CLUSTERS}
            dominant = "structural"
        else:
            percentages = {
                c: round(counts[c] / total * 100, 1)
                for c in _CLUSTERS
            }
            dominant = max(counts, key=lambda c: counts[c])

        return {
            "clusters":             percentages,
            "dominant":             dominant,
            "total_content_words":  total,
            "author_reality":       _AUTHOR_REALITY[dominant],
            "reader_deficit":       _READER_DEFICIT[dominant],
            "is_posturing":         self._detect_posturing(dominant),
        }

    # ------------------------------------------------------------------
    def _detect_posturing(self, lexical_dominant: str) -> bool:
        """
        True when the macro-semantic dominant pole is kinetic/aggression
        but the subconscious graphemic preference is structural/safety —
        the classic Posturing signature.
        """
        if not self._macro:
            return False
        best_cluster = best_pole = None
        best_score = -1.0
        for cluster, poles in self._macro.items():
            for pole, score in poles.items():
                if score > best_score:
                    best_score   = score
                    best_cluster = cluster
                    best_pole    = pole
        return (
            best_cluster == "kinetic"
            and best_pole == "aggression"
            and lexical_dominant == "structural"
        )
