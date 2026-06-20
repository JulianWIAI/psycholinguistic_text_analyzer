"""
Macro-Layer Semantic Clusters — Chinese (ZH)
6-cluster operational/steganographic dictionaries for Mandarin Chinese.

Uses jieba for word segmentation + exact substring matching against the
cluster dictionaries. No spaCy model required (avoids mandatory zh model
download on first run).

Clusters: Resources, Power, Visibility, Temporal, Cognitive, Kinetic
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from macro_layer.semantic_analyzer import MacroScore, ClusterHit

# ---------------------------------------------------------------------------
# Optional jieba tokenizer
# ---------------------------------------------------------------------------
try:
    import jieba
    _JIEBA_AVAILABLE = True
except ImportError:
    _JIEBA_AVAILABLE = False
    warnings.warn(
        "jieba not installed — ZH macro tokenization will be character-level. "
        "Install with: pip install jieba",
        RuntimeWarning, stacklevel=2,
    )


# ---------------------------------------------------------------------------
# Chinese semantic cluster dictionaries
# ---------------------------------------------------------------------------
ZH_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "配给", "赤字", "饥饿", "短缺", "枯竭", "匮乏", "制约", "削减",
            "剥夺", "限制", "节制", "紧缩", "冻结", "消耗", "紧张", "贫乏",
            "不足", "缺少", "减少", "吃紧", "拮据", "节约", "窘迫", "贫困",
        ],
        "abundance": [
            "过剩", "充裕", "豪华", "资产", "富裕", "溢出", "慷慨", "充足",
            "繁荣", "丰富", "宽裕", "浪费", "奢侈", "财富", "盈余", "充沛",
            "丰盛", "大量", "充实", "富饶", "富有", "盛产", "涌现", "充盈",
        ],
    },
    "power": {
        "control": [
            "强制", "命令", "权限", "统制", "指挥", "支配", "统治", "监视",
            "规制", "管控", "封锁", "压制", "掌控", "主导", "领导", "专制",
            "独裁", "集权", "管辖", "约束", "强行", "命令", "镇压", "制裁",
            "号令", "执法", "授权", "批准", "审批", "裁决", "处置", "干预",
        ],
        "submission": [
            "服从", "顺从", "屈服", "妥协", "接受", "承受", "依从", "降服",
            "让步", "听命", "奉命", "遵从", "受制", "被迫", "压力", "忍受",
            "顺应", "配合", "照办", "执行", "依照", "遵守", "合规", "服务",
        ],
    },
    "visibility": {
        "concealment": [
            "隐藏", "保密", "秘密", "掩盖", "封锁", "压制", "隐瞒", "遮蔽",
            "屏蔽", "删除", "审查", "过滤", "消声", "封口", "遮掩", "隐秘",
            "不透明", "黑箱", "幕后", "暗中", "私下", "暗操", "遮蔽", "压制",
        ],
        "exposure": [
            "披露", "揭露", "公开", "透明", "曝光", "揭示", "发布", "公示",
            "发现", "爆料", "揭发", "报告", "声明", "公布", "告知", "通报",
            "宣告", "宣传", "昭告", "明示", "展示", "呈现", "显示", "表达",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "传统", "历史", "古代", "旧时", "从前", "过去", "遗产", "经典",
            "昔日", "往昔", "怀旧", "复古", "回顾", "纪念", "追忆", "历史",
            "根源", "原始", "祖先", "民族", "传承", "文化", "遗迹", "故事",
        ],
        "future_projective": [
            "威胁", "危机", "风险", "警告", "预测", "预警", "入侵", "灾难",
            "战争", "冲突", "对抗", "进攻", "侵略", "崩溃", "瓦解", "毁灭",
            "即将", "紧迫", "迫在眉睫", "危险", "告急", "紧急", "告警", "预见",
        ],
    },
    "cognitive": {
        "scientific": [
            "数据", "证明", "分析", "研究", "统计", "测量", "系统", "方法",
            "模型", "算法", "实验", "验证", "量化", "精确", "科学", "技术",
            "理论", "原理", "逻辑", "客观", "事实", "结论", "报告", "评估",
        ],
        "emotional": [
            "感觉", "情感", "心情", "感受", "本能", "直觉", "情绪", "内心",
            "精神", "灵魂", "信念", "意志", "信仰", "激情", "热情", "渴望",
            "恐惧", "愤怒", "悲伤", "喜悦", "希望", "绝望", "痛苦", "快乐",
        ],
    },
    "kinetic": {
        "aggression": [
            "打击", "突破", "排除", "攻击", "强袭", "破坏", "压制", "侵入",
            "粉碎", "压倒", "爆炸", "动员", "交战", "歼灭", "掌握", "捕获",
            "制压", "侵攻", "占领", "打倒", "袭击", "轰炸", "摧毁", "清除",
        ],
        "diplomacy": [
            "谈判", "维持", "条约", "均衡", "停火", "对话", "调解", "稳定",
            "延迟", "和解", "妥协", "撤退", "监视", "温和", "让步", "解决",
            "协议", "协商", "缓和", "合作", "共识", "外交", "和平", "协调",
        ],
    },
}

# Flat exact-match lookup: word → (cluster, pole, weight)
_ZH_WORD_LOOKUP: Dict[str, Tuple[str, str, float]] = {}
for _cluster, _poles in ZH_CLUSTERS.items():
    for _pole, _words in _poles.items():
        for _w in _words:
            _ZH_WORD_LOOKUP[_w] = (_cluster, _pole, 1.0)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class ChineseSemanticAnalyzer:
    """
    6-cluster semantic analyzer for Chinese text.

    Uses jieba for word segmentation; exact-match against ZH_CLUSTERS.
    No spaCy model required.
    """

    def analyze(self, text: str) -> MacroScore:
        if _JIEBA_AVAILABLE:
            tokens = [w for w in jieba.cut(text) if w.strip()]
        else:
            tokens = list(text)

        total_tokens = max(1, len(tokens))
        raw: Dict[str, Dict[str, float]] = {}
        hits: List[ClusterHit] = []

        for token in tokens:
            match = _ZH_WORD_LOOKUP.get(token)
            if match is None:
                # Also try multi-character matches (compound nouns in jieba output)
                for phrase, entry in _ZH_WORD_LOOKUP.items():
                    if phrase in token:
                        match = entry
                        break
            if match:
                cluster, pole, weight = match
                raw.setdefault(cluster, {}).setdefault(pole, 0.0)
                raw[cluster][pole] += weight
                hits.append(ClusterHit(lemma=token, cluster=cluster, pole=pole, weight=weight))

        # Ensure all 6 clusters have both poles (even if zero)
        for cluster, poles in ZH_CLUSTERS.items():
            raw.setdefault(cluster, {})
            for pole in poles:
                raw[cluster].setdefault(pole, 0.0)

        normalized: Dict[str, Dict[str, float]] = {
            cluster: {pole: score / total_tokens for pole, score in poles.items()}
            for cluster, poles in raw.items()
        }

        return MacroScore(cluster_scores=normalized, total_words=total_tokens, hits=hits)
