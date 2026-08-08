"""
graph_layer/feature_extractor.py
---------------------------------
Shared helpers that convert analysis-result dicts into (node_id, node_type,
properties, weight) tuples for both the persistent graph (index_document)
and the ephemeral matrix builder.

All public functions return a list of FeatureRecord named-tuples so callers
can iterate once and decide whether to add graph nodes or accumulate matrix
co-occurrences.
"""

from typing import Any, Dict, List, NamedTuple, Optional

# Minimum weight below which a feature is not emitted.
# Keeps the matrix sparse and meaningful.
_MIN_WEIGHT = 0.05


class FeatureRecord(NamedTuple):
    node_id:   str    # e.g. "pds_anger", "field_nature", "device_anaphora"
    node_type: str    # graph node type string
    props:     dict   # properties stored on the node
    weight:    float  # co-occurrence edge weight


# ---------------------------------------------------------------------------
# Stylistic devices  (from literary.rhetorical_findings)
# ---------------------------------------------------------------------------

def extract_literary_features(literary: Optional[Dict[str, Any]]) -> List[FeatureRecord]:
    """Extract StylisticDevice and WordField records from a literary result dict."""
    records: List[FeatureRecord] = []
    if not isinstance(literary, dict):
        return records

    # Rhetorical devices
    for finding in literary.get("rhetorical_findings", []) or []:
        if not isinstance(finding, dict):
            continue
        dtype = finding.get("device_type") or finding.get("type")
        if not dtype:
            continue
        records.append(FeatureRecord(
            node_id   = f"device_{dtype.lower()}",
            node_type = "StylisticDevice",
            props     = {"device": dtype},
            weight    = 1.0,
        ))

    # Word field densities
    field_density = (literary.get("word_fields") or {}).get("field_density") or {}
    for field_name, density in field_density.items():
        val = float(density) if density is not None else 0.0
        if val < _MIN_WEIGHT:
            continue
        records.append(FeatureRecord(
            node_id   = f"field_{field_name.lower()}",
            node_type = "WordField",
            props     = {"field": field_name},
            weight    = val,
        ))

    return records


# ---------------------------------------------------------------------------
# Macro cluster scores  (from macro.cluster_scores or macro_scores dict)
# ---------------------------------------------------------------------------

def extract_macro_features(macro_scores: Optional[Dict[str, Any]]) -> List[FeatureRecord]:
    """Extract MacroCluster records from a {cluster: {pole: score}} dict."""
    records: List[FeatureRecord] = []
    if not isinstance(macro_scores, dict):
        return records

    for cluster, score_data in macro_scores.items():
        if isinstance(score_data, dict):
            combined = sum(
                abs(float(v)) for v in score_data.values()
                if isinstance(v, (int, float))
            )
        elif isinstance(score_data, (int, float)):
            combined = abs(float(score_data))
        else:
            combined = 0.0

        if combined < _MIN_WEIGHT:
            continue

        records.append(FeatureRecord(
            node_id   = f"cluster_{cluster.lower()}",
            node_type = "MacroCluster",
            props     = {"cluster": cluster},
            weight    = combined,
        ))

    return records


# ---------------------------------------------------------------------------
# Somatic archetype  (from somatic dict)
# ---------------------------------------------------------------------------

def extract_somatic_features(somatic: Optional[Dict[str, Any]]) -> List[FeatureRecord]:
    """Extract SomaticArchetype record from a somatic result dict."""
    records: List[FeatureRecord] = []
    if not isinstance(somatic, dict):
        return records

    archetype = somatic.get("quersumme_archetype") or somatic.get("archetype")
    if archetype:
        records.append(FeatureRecord(
            node_id   = f"somatic_{archetype.lower().replace(' ', '_')}",
            node_type = "SomaticArchetype",
            props     = {"archetype": archetype},
            weight    = 1.0,
        ))

    return records


# ---------------------------------------------------------------------------
# PDS / VAD affect feelings  (from psychological_payload)
# ---------------------------------------------------------------------------

# Maps payload key → (node suffix, label shown in the graph)
# The "pds_" prefix is added automatically so the frontend colour-codes them.
_PDS_EMOTION_KEYS: List[tuple] = [
    # 8-axis NRC affect intensities (range 0–1)
    ("anger_mean",    "anger",        "Anger"),
    ("fear_mean",     "fear",         "Fear"),
    ("joy_mean",      "joy",          "Joy"),
    ("sad_mean",      "sadness",      "Sadness"),
    ("dis_mean",      "disgust",      "Disgust"),
    ("ant_mean",      "anticipation", "Anticipation"),
    ("tru_mean",      "trust",        "Trust"),
    ("sur_mean",      "surprise",     "Surprise"),
    # PDS axes (range –1 … +1 → use absolute magnitude as weight)
    ("power_mean",    "power",        "Power"),
    ("danger_mean",   "danger",       "Danger"),
    ("structure_mean","structure",    "Structure"),
    # VAD (range –1 … +1 → absolute magnitude)
    ("valence_mean",  "valence",      "Valence"),
    ("arousal_mean",  "arousal",      "Arousal"),
    ("dominance_mean","dominance",    "Dominance"),
]


def extract_affect_features(
    psychological_payload: Optional[Dict[str, Any]]
) -> List[FeatureRecord]:
    """
    Extract AffectNode records from a psychological_payload dict.

    Each emotion dimension whose mean score exceeds the minimum threshold
    becomes a 'pds_<emotion>' feature node.  The edge weight equals the
    absolute mean value so the matrix captures affect intensity, not sign.
    """
    records: List[FeatureRecord] = []
    if not isinstance(psychological_payload, dict):
        return records

    for payload_key, node_suffix, label in _PDS_EMOTION_KEYS:
        raw = psychological_payload.get(payload_key)
        if raw is None:
            continue
        weight = abs(float(raw))
        if weight < _MIN_WEIGHT:
            continue
        records.append(FeatureRecord(
            node_id   = f"pds_{node_suffix}",
            node_type = "AffectNode",
            props     = {"affect": label},
            weight    = weight,
        ))

    return records
