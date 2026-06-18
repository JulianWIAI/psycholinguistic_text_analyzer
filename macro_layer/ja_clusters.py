"""
Macro-Layer Semantic Clusters — Japanese (JA)
Japanese translations of the four base semantic clusters, plus a dedicated
Keigo (敬語 / honorific register) analysis layer.

Keigo/Hierarchy Layer:
    High Keigo density   → Submission/Distance vector (psycholinguistic distance,
                            deference, institutional compliance)
    Drop in Keigo usage  → Assertion/Proximity vector (directness, familiarity,
                            power assertion from author toward reader)

This module provides:
    JA_CLUSTERS   — word lists for the four standard clusters (lemma form)
    KeigoBowAnalyzer — detects honorific register markers in raw text
    JapaneseSemanticAnalyzer — combines cluster scoring + Keigo analysis
                                and returns a standard MacroScore
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from macro_layer.semantic_analyzer import MacroScore, ClusterHit

# ---------------------------------------------------------------------------
# Japanese semantic cluster dictionaries
# Words should match the lemma form returned by ja_core_news_sm
# ---------------------------------------------------------------------------
JA_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "不足", "制限", "予算", "少ない", "欠乏", "厳しい",
            "削減", "節約", "制約", "乏しい", "逼迫", "枯渇",
        ],
        "abundance": [
            "豊富", "大量", "無限", "余裕", "過剰", "豊か",
            "充実", "潤沢", "満ち", "繁栄", "豊盛", "豊饒",
        ],
    },
    "power": {
        "control": [
            "管理", "命令", "支配", "制御", "統治", "命じる",
            "規制", "権力", "強制", "統制", "掌握", "指揮",
        ],
        "submission": [
            "従う", "服従", "受け入れる", "従属", "強いられる",
            "従事", "服す", "甘んじる", "委ねる", "恭順",
        ],
    },
    "visibility": {
        "concealment": [
            "隠す", "秘密", "密か", "曖昧", "隠蔽", "闇",
            "蔽う", "覆い", "黙秘", "隠匿", "不透明",
        ],
        "exposure": [
            "明らか", "公開", "透明", "明示", "暴露", "示す",
            "明白", "公明", "開示", "露呈", "顕在",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "過去", "伝統", "歴史", "昔", "記憶", "回顧",
            "復元", "懐かしい", "旧来", "往昔", "故郷",
        ],
        "future_projective": [
            "未来", "将来", "前進", "革新", "展望", "次",
            "発展", "進歩", "展開", "先進", "飛躍",
        ],
    },
}

# ---------------------------------------------------------------------------
# Keigo (敬語) pattern registry
# Each entry: (pattern_string, weight, keigo_class)
# Higher weight = more formal / greater psycholinguistic distance
# ---------------------------------------------------------------------------
_KEIGO_PATTERNS: List[Tuple[str, float, str]] = [
    # Ultra-formal (sonkeigo + kenjōgo at maximum distance)
    ("ございます",   2.5, "ultra_formal"),
    ("いたします",   2.5, "ultra_formal"),
    ("おります",     2.0, "ultra_formal"),
    ("申します",     2.0, "ultra_formal"),
    ("いただきます", 2.0, "ultra_formal"),
    ("くださいます", 2.0, "ultra_formal"),
    # Respectful (sonkeigo)
    ("いらっしゃ",   1.8, "sonkeigo"),
    ("おっしゃ",     1.8, "sonkeigo"),
    ("なさいます",   1.8, "sonkeigo"),
    ("くださ",       1.5, "sonkeigo"),
    ("ご覧",         1.5, "sonkeigo"),
    # Humble (kenjōgo)
    ("まいります",   1.5, "kenjoogo"),
    ("いただ",       1.5, "kenjoogo"),
    ("存じます",     1.8, "kenjoogo"),
    # Standard polite (teineigo)
    ("ます",         1.0, "teineigo"),
    ("ました",       1.0, "teineigo"),
    ("ません",       1.0, "teineigo"),
    ("でございます", 2.0, "teineigo"),
    ("です",         0.8, "teineigo"),
    ("でした",       0.8, "teineigo"),
    ("でしょう",     0.8, "teineigo"),
    # Honorific prefixes (productive — o/go + noun)
    ("お",           0.4, "prefix"),
    ("ご",           0.5, "prefix"),
    # Plain/casual markers — signal ABSENCE of keigo (negative weight)
    ("だよ",        -0.8, "casual"),
    ("じゃない",    -1.0, "casual"),
    ("だろう",      -0.6, "casual"),
    ("だな",        -0.8, "casual"),
    ("っていう",    -0.6, "casual"),
]

# Compile patterns for efficiency
_COMPILED_PATTERNS: List[Tuple[re.Pattern, float, str]] = [
    (re.compile(re.escape(pat)), weight, klass)
    for pat, weight, klass in _KEIGO_PATTERNS
]


class KeigoBowAnalyzer:
    """
    Bag-of-patterns Keigo register detector.

    Returns a (formal_score, casual_score) pair normalized per 100 characters.
    Formal score > 1.5 (per 100 chars) = strong institutional submission framing.
    Casual score > 1.0 = assertion / proximity framing.
    """

    def analyze(self, text: str) -> Tuple[float, float]:
        n = max(1, len(text))
        formal_total  = 0.0
        casual_total  = 0.0

        for pattern, weight, klass in _COMPILED_PATTERNS:
            hits = len(pattern.findall(text))
            if hits == 0:
                continue
            if weight >= 0:
                formal_total += weight * hits
            else:
                casual_total += abs(weight) * hits

        # Normalize to per-100-character rate
        return (
            round(formal_total / n * 100, 4),
            round(casual_total / n * 100, 4),
        )


# ---------------------------------------------------------------------------
# Japanese Semantic Analyzer (replaces SemanticAnalyzer for JA)
# ---------------------------------------------------------------------------

class JapaneseSemanticAnalyzer:
    """
    Combines cluster-based word matching (via spaCy) with Keigo analysis.

    The 'keigo' pseudo-cluster is injected into the MacroScore so the
    dissonance engine receives a unified macro signal regardless of language.
    """

    def __init__(self):
        from language.registry import ModelRegistry
        self._nlp     = ModelRegistry.load("ja_core_news_sm")
        self._keigo   = KeigoBowAnalyzer()
        self._lookup  = self._build_lookup()

    def _build_lookup(self) -> Dict[str, Tuple[str, str, float]]:
        lookup: Dict[str, Tuple[str, str, float]] = {}
        for cluster, poles in JA_CLUSTERS.items():
            for pole, words in poles.items():
                for w in words:
                    lookup[w] = (cluster, pole, 1.0)
        return lookup

    def analyze(self, text: str) -> MacroScore:
        doc = self._nlp(text)
        total_tokens = max(1, len([t for t in doc if not t.is_space]))

        # Cluster scoring via lemma matching
        raw: Dict[str, Dict[str, float]] = {
            cluster: {pole: 0.0 for pole in poles}
            for cluster, poles in JA_CLUSTERS.items()
        }
        hits: List[ClusterHit] = []

        for token in doc:
            lemma = token.lemma_
            if lemma in self._lookup:
                cluster, pole, weight = self._lookup[lemma]
                raw[cluster][pole] += weight
                hits.append(ClusterHit(lemma=lemma, cluster=cluster, pole=pole, weight=weight))

        normalized: Dict[str, Dict[str, float]] = {
            cluster: {
                pole: score / total_tokens
                for pole, score in poles.items()
            }
            for cluster, poles in raw.items()
        }

        # Keigo analysis — injected as an extra pseudo-cluster
        formal, casual = self._keigo.analyze(text)
        normalized["keigo"] = {
            "formal":   formal,   # → Submission / Distance
            "casual":   casual,   # → Assertion / Proximity
        }

        return MacroScore(
            cluster_scores=normalized,
            total_words=total_tokens,
            hits=hits,
        )
