"""
Macro-Layer Semantic Clusters — Japanese (JA)
6-cluster operational/steganographic dictionaries, plus dedicated
Keigo (敬語 / honorific register) analysis layer.

Keigo/Hierarchy Layer:
    High Keigo density   → Submission/Distance vector
    Drop in Keigo usage  → Assertion/Proximity vector

Clusters: Resources, Power, Visibility, Temporal, Cognitive, Kinetic
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from macro_layer.semantic_analyzer import MacroScore, ClusterHit

# ---------------------------------------------------------------------------
# Japanese semantic cluster dictionaries (lemma / dictionary form)
# ---------------------------------------------------------------------------
JA_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "配給", "赤字", "飢餓", "厳格", "締め付け",
            "不足", "欠乏", "制約", "枯渇", "最小限",
            "節制", "緊縮", "凍結", "削減", "剥奪",
            "制限", "予算", "消耗", "干上がる", "逼迫",
            "少ない", "乏しい", "倹約", "窮乏", "節約",
        ],
        "abundance": [
            "余剰", "氾濫", "豪華", "無限", "資産",
            "富", "溢れる", "寛大", "十分", "豊富",
            "繁栄", "過剰", "潤沢", "余裕", "浪費",
            "贅沢", "宝", "流れる", "隆盛", "満たす",
            "豊か", "大量", "充実", "豊饒", "潤う",
        ],
    },
    "power": {
        "control": [
            "強制", "命令", "権限", "統制", "展開",
            "指揮", "支配", "統治", "監視", "義務付ける",
            "規制", "覆す", "封じ込め", "管理", "執行",
            "誘導", "封鎖", "制御", "抑圧", "権力",
            "掌握", "命じる", "統率", "号令", "制圧",
        ],
        "submission": [
            "耐える", "割り当て", "強いられ", "流される", "従う",
            "服従", "承服", "従属", "受け入れる", "降参",
            "容認", "屈服", "拘禁", "圧力", "耐え忍ぶ",
            "黙認", "従順", "服する", "甘んじる", "委ねる",
            "恭順", "隷属", "服い", "従い", "諦める",
        ],
    },
    "visibility": {
        "concealment": [
            "隠蔽", "傍受", "覆い", "暗号化", "影",
            "隠す", "偽装", "仮面", "埋没", "抑圧",
            "潜む", "擬装", "選別", "迂回", "封印",
            "緘黙", "秘密", "曖昧", "密か", "不透明",
            "闇", "黙秘", "隠匿", "沈める", "不可視",
        ],
        "exposure": [
            "放送", "明確", "明らか", "表面", "明るい",
            "暴露", "公開", "透明", "開放", "可視",
            "照らす", "示す", "表示", "信号", "発表",
            "露骨", "開示", "宣言", "明示", "発見",
            "公明", "露呈", "顕在", "明白", "公示",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "根源", "復元", "記憶", "以前", "遺産",
            "回帰", "伝統", "旧来", "回想", "追憶",
            "起源", "遺物", "郷愁", "先祖", "過去",
            "歴史", "昔", "回顧", "懐かしい", "往昔",
            "故郷", "旧", "原点", "由来", "創設",
        ],
        "future_projective": [
            "地平", "到来", "前進", "脅威", "軌跡",
            "進歩", "革新", "出現", "展望", "標的",
            "激化", "展開", "予測", "急増", "収束",
            "予感", "集結", "予報", "前進する", "未来",
            "将来", "発展", "先進", "飛躍", "次",
        ],
    },
    "cognitive": {
        "scientific": [
            "計算", "変数", "物理", "指標", "観察",
            "構造", "分析", "実証", "パラメータ", "測定",
            "定量化", "モデル", "データ", "仮説", "体系",
            "論理", "数式", "実験", "証拠", "検証",
            "較正", "分類", "精度", "アルゴリズム", "導出",
        ],
        "emotional": [
            "感情", "希望", "魂", "絶望", "直感",
            "抽象", "信念", "夢", "苦悩", "悲嘆",
            "愛情", "恐怖", "痛み", "切望", "悼み",
            "苦悶", "想像", "渇望", "共感", "悲しみ",
            "情熱", "願い", "真心", "本能", "感受性",
        ],
    },
    "kinetic": {
        "aggression": [
            "打撃", "突破", "排除", "標的", "攻撃",
            "強襲", "破壊", "無力化", "侵入", "粉砕",
            "圧倒", "急襲", "爆発", "動員", "交戦",
            "殲滅", "掌握", "捕捉", "撃滅", "撃つ",
            "制圧", "侵攻", "占領", "破砕", "打倒",
        ],
        "diplomacy": [
            "交渉", "維持", "遅延", "条約", "均衡",
            "停戦", "対話", "仲裁", "安定化", "延期",
            "和解", "妥協", "撤退", "監視", "観察",
            "抑制", "温和", "譲歩", "解決", "合意",
            "収束", "調停", "和平", "緩和", "協調",
        ],
    },
}

# ---------------------------------------------------------------------------
# Keigo (敬語) pattern registry
# ---------------------------------------------------------------------------
_KEIGO_PATTERNS: List[Tuple[str, float, str]] = [
    ("ございます",   2.5, "ultra_formal"),
    ("いたします",   2.5, "ultra_formal"),
    ("おります",     2.0, "ultra_formal"),
    ("申します",     2.0, "ultra_formal"),
    ("いただきます", 2.0, "ultra_formal"),
    ("くださいます", 2.0, "ultra_formal"),
    ("いらっしゃ",   1.8, "sonkeigo"),
    ("おっしゃ",     1.8, "sonkeigo"),
    ("なさいます",   1.8, "sonkeigo"),
    ("くださ",       1.5, "sonkeigo"),
    ("ご覧",         1.5, "sonkeigo"),
    ("まいります",   1.5, "kenjoogo"),
    ("いただ",       1.5, "kenjoogo"),
    ("存じます",     1.8, "kenjoogo"),
    ("ます",         1.0, "teineigo"),
    ("ました",       1.0, "teineigo"),
    ("ません",       1.0, "teineigo"),
    ("でございます", 2.0, "teineigo"),
    ("です",         0.8, "teineigo"),
    ("でした",       0.8, "teineigo"),
    ("でしょう",     0.8, "teineigo"),
    ("お",           0.4, "prefix"),
    ("ご",           0.5, "prefix"),
    ("だよ",        -0.8, "casual"),
    ("じゃない",    -1.0, "casual"),
    ("だろう",      -0.6, "casual"),
    ("だな",        -0.8, "casual"),
    ("っていう",    -0.6, "casual"),
]

_COMPILED_PATTERNS: List[Tuple[re.Pattern, float, str]] = [
    (re.compile(re.escape(pat)), weight, klass)
    for pat, weight, klass in _KEIGO_PATTERNS
]


class KeigoBowAnalyzer:
    """Bag-of-patterns Keigo register detector."""

    def analyze(self, text: str) -> Tuple[float, float]:
        n = max(1, len(text))
        formal_total = 0.0
        casual_total = 0.0
        for pattern, weight, klass in _COMPILED_PATTERNS:
            hits = len(pattern.findall(text))
            if hits == 0:
                continue
            if weight >= 0:
                formal_total += weight * hits
            else:
                casual_total += abs(weight) * hits
        return (
            round(formal_total / n * 100, 4),
            round(casual_total / n * 100, 4),
        )


class JapaneseSemanticAnalyzer:
    """
    Combines 6-cluster word matching with Keigo register analysis.
    Uses VectorClusterScorer (cosine similarity) when ja_core_news_md is
    available; falls back to exact-match with ja_core_news_sm.
    """

    def __init__(self):
        from macro_layer.semantic_analyzer import VectorClusterScorer, _load_spacy
        self._nlp    = _load_spacy("ja_core_news_md")
        self._keigo  = KeigoBowAnalyzer()
        self._lookup = self._build_lookup()
        self._scorer = VectorClusterScorer(
            nlp=self._nlp,
            clusters=JA_CLUSTERS,
            exact_lookup=self._lookup,
        )

    def _build_lookup(self) -> Dict[str, Tuple[str, str, float]]:
        lookup: Dict[str, Tuple[str, str, float]] = {}
        for cluster, poles in JA_CLUSTERS.items():
            for pole, words in poles.items():
                for w in words:
                    lookup[w.lower()] = (cluster, pole, 1.0)
        return lookup

    def analyze(self, text: str) -> MacroScore:
        doc = self._nlp(text)
        content_tokens = [t for t in doc if not t.is_space]
        total_tokens = max(1, len(content_tokens))

        raw, hits = self._scorer.score_tokens(content_tokens)

        normalized: Dict[str, Dict[str, float]] = {
            cluster: {pole: score / total_tokens for pole, score in poles.items()}
            for cluster, poles in raw.items()
        }

        formal, casual = self._keigo.analyze(text)
        normalized["keigo"] = {"formal": formal, "casual": casual}

        return MacroScore(cluster_scores=normalized, total_words=total_tokens, hits=hits)
