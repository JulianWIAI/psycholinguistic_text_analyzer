"""
MODULE 2-ZH — Chinese Orthographic Micro-Layer
Universal Tokenization Override: Converts Hanzi → Pinyin via pypinyin,
passes the phonetic string to the C++ BPV engine, then merges native
jieba-based character/word counts back into the result.

Dual-Signal Physics Engine:
    Simultaneously maps every Hanzi character to its stroke count, producing
    an ordered stroke_count_array that captures the physical ink density of
    the window. A sudden spike in stroke counts signals a switch to massively
    complex ideograms — a prime indicator of hidden data or bureaucratic masking.

Fallback chain:
    C++ + jieba + pypinyin (full pipeline)
    → jieba + pypinyin (if C++ unavailable; stroke-only vectors)
    → character-by-character fallback (if jieba unavailable)
"""

import unicodedata
import warnings
from typing import List, Optional

from micro_layer.base_analyzer import BaseMicroAnalyzer, MicroResult

# ---------------------------------------------------------------------------
# Optional C++ core
# ---------------------------------------------------------------------------
try:
    import psycho_core as _core
    _CPP_AVAILABLE = True
except ImportError:
    _core = None
    _CPP_AVAILABLE = False

# ---------------------------------------------------------------------------
# Optional jieba tokenizer
# ---------------------------------------------------------------------------
try:
    import jieba
    _JIEBA_AVAILABLE = True
except ImportError:
    _JIEBA_AVAILABLE = False
    warnings.warn(
        "jieba not installed — ZH word tokenization will be character-level. "
        "Install with: pip install jieba",
        RuntimeWarning, stacklevel=2,
    )

# ---------------------------------------------------------------------------
# Optional pypinyin romanizer
# ---------------------------------------------------------------------------
try:
    from pypinyin import lazy_pinyin
    _PYPINYIN_AVAILABLE = True
except ImportError:
    _PYPINYIN_AVAILABLE = False
    warnings.warn(
        "pypinyin not installed — ZH romanization unavailable. "
        "Install with: pip install pypinyin",
        RuntimeWarning, stacklevel=2,
    )


# ---------------------------------------------------------------------------
# Hanzi stroke count lookup — common Simplified Chinese characters
# Source: GB 2312 stroke-count reference + standard primary-school corpus
# Unknown characters fall back to FALLBACK_STROKE_COUNT.
# ---------------------------------------------------------------------------
ZH_STROKE_COUNT = {
    # Numbers / units
    "一": 1, "二": 2, "三": 3, "四": 5, "五": 4, "六": 4, "七": 2, "八": 2,
    "九": 2, "十": 2, "百": 6, "千": 3, "万": 3, "元": 4, "亿": 3,
    # Pronouns / particles
    "的": 8, "了": 2, "在": 6, "是": 9, "我": 7, "你": 7, "他": 5, "她": 6,
    "它": 5, "们": 5, "这": 7, "那": 6, "有": 6, "没": 7, "不": 4, "也": 3,
    "都": 11, "和": 8, "与": 3, "或": 8, "从": 4, "把": 7, "被": 10,
    "让": 5, "叫": 5, "比": 4, "向": 6, "对": 5, "到": 8, "为": 4,
    "以": 4, "可": 5, "将": 9, "而": 6, "但": 7, "如": 6, "所": 8,
    # Time
    "年": 6, "月": 4, "日": 4, "时": 7, "分": 4, "秒": 9, "周": 8, "今": 4,
    "明": 8, "昨": 9, "前": 9, "后": 6, "早": 6, "晚": 11, "现": 8, "过": 6,
    # People / body
    "人": 2, "口": 3, "目": 5, "手": 4, "足": 7, "心": 4, "体": 7, "头": 5,
    "耳": 6, "眼": 11, "鼻": 14, "脸": 10, "腿": 13, "臂": 17, "身": 7,
    "骨": 10, "血": 6, "肉": 6, "皮": 5, "脑": 10,
    # Nature
    "山": 3, "川": 3, "海": 10, "空": 8, "木": 4, "花": 7, "火": 4, "水": 4,
    "土": 3, "金": 8, "雨": 8, "雪": 11, "风": 4, "石": 5, "草": 9, "林": 8,
    "树": 9, "云": 4, "江": 6, "河": 8, "湖": 12, "山": 3, "地": 6, "天": 4,
    # Size / quality
    "大": 3, "小": 3, "高": 10, "低": 7, "长": 4, "短": 12, "多": 6, "少": 4,
    "好": 6, "坏": 7, "新": 13, "旧": 5, "重": 9, "轻": 9, "强": 11, "弱": 10,
    "快": 7, "慢": 14, "硬": 12, "软": 8, "冷": 7, "热": 10,
    # Direction / position
    "东": 5, "西": 6, "南": 9, "北": 5, "上": 3, "下": 3, "左": 5, "右": 5,
    "中": 4, "外": 5, "里": 7, "间": 7, "内": 4, "旁": 10,
    # Country / governance
    "国": 8, "市": 5, "省": 9, "县": 7, "家": 10, "部": 11, "室": 9,
    "政": 9, "府": 8, "党": 10, "军": 6, "民": 5, "官": 8, "法": 8,
    "律": 9, "院": 9, "委": 8, "会": 6, "局": 7, "署": 13, "厅": 5,
    # Actions
    "说": 9, "看": 9, "听": 7, "写": 5, "读": 10, "走": 7, "来": 7, "去": 5,
    "吃": 6, "喝": 12, "买": 6, "卖": 8, "用": 5, "做": 11, "开": 4, "关": 6,
    "进": 7, "出": 5, "回": 6, "问": 6, "想": 13, "知": 8, "得": 11, "给": 9,
    "使": 8, "打": 5, "找": 7, "放": 8, "发": 5, "取": 8, "带": 9,
    # Power / control / surveillance
    "权": 6, "力": 2, "命": 8, "令": 5, "制": 8, "度": 9, "规": 11, "则": 9,
    "控": 11, "监": 10, "督": 13, "领": 14, "导": 6, "指": 9, "挥": 12,
    "统": 9, "治": 8, "支": 4, "配": 10, "属": 12, "服": 8, "压": 6,
    "管": 14, "理": 11, "权力": 6, "授权": 6, "执法": 8, "制裁": 8,
    "审": 15, "查": 9, "批": 7, "准": 10, "许": 11, "禁": 13, "止": 4,
    # Concealment / revelation
    "隐": 11, "秘": 10, "密": 11, "影": 15, "暗": 13, "明": 8, "示": 5,
    "公": 4, "表": 8, "现": 8, "藏": 17, "掩": 12, "盖": 11, "揭": 12,
    "露": 21, "透": 10, "泄": 8, "封": 9, "堵": 12,
    # Communication / media / propaganda
    "话": 8, "文": 4, "字": 6, "报": 7, "网": 6, "信": 9, "传": 6, "播": 15,
    "发": 5, "布": 5, "声": 7, "音": 9, "媒": 12, "息": 10, "语": 14,
    "讲": 17, "述": 8, "叙": 11, "描": 11, "述": 8,
    # Economy / resources
    "钱": 10, "财": 7, "资": 10, "银": 11, "产": 6, "业": 5, "经": 8,
    "济": 9, "贸": 9, "易": 8, "贫": 8, "富": 12, "税": 12, "款": 12,
    # Military / conflict
    "战": 9, "争": 6, "武": 8, "器": 16, "炸": 9, "击": 5, "攻": 7,
    "守": 6, "防": 7, "敌": 15, "兵": 7, "导弹": 9, "核": 10,
    # Emotion / psychology
    "爱": 10, "恨": 10, "怒": 9, "悲": 12, "喜": 12, "恐": 10, "怕": 8,
    "痛": 12, "苦": 8, "乐": 5, "愁": 13, "忧": 7, "恶": 10, "善": 12,
    "怀": 8, "念": 8, "望": 11, "盼": 9,
}

FALLBACK_STROKE_COUNT: int = 8  # median stroke count for unrecognized Hanzi


# ---------------------------------------------------------------------------
# Character helpers
# ---------------------------------------------------------------------------

def _is_hanzi(ch: str) -> bool:
    """Return True for CJK Unified Ideographs (U+4E00–U+9FFF)."""
    return "一" <= ch <= "鿿"


def _is_meaningful(ch: str) -> bool:
    """Exclude whitespace and CJK punctuation from counts."""
    if ch in (" ", "\n", "\t", "\r"):
        return False
    cat = unicodedata.category(ch)
    return not (cat.startswith("P") or cat.startswith("Z"))


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class ChineseOrthographicAnalyzer(BaseMicroAnalyzer):
    """
    Chinese micro-layer analyzer — Universal Tokenization Override.

    Pipeline
    --------
    1. Native tokenization via jieba → true word count + char count
    2. Per-character stroke array (physical ink density signal)
    3. Pinyin romanization via pypinyin (space-separated words)
    4. C++ BPV engine on the phonetic Pinyin string → psychological vectors
    5. Merge: replace C++ structural counts with native jieba counts;
       inject stroke_count_array into raw for the Dual-Signal oscilloscope
    """

    @property
    def language_code(self) -> str:
        return "ZH"

    def analyze(self, text: str) -> MicroResult:
        # ── 1. Native tokenization ─────────────────────────────────────────────
        if _JIEBA_AVAILABLE:
            words = [w for w in jieba.cut(text) if w.strip()]
        else:
            # Character-level fallback: each meaningful character is a "word"
            words = [ch for ch in text if _is_meaningful(ch)]

        true_native_char_count    = sum(len(w) for w in words)
        true_tokenized_word_count = len(words)

        # ── 2. Stroke count array ─────────────────────────────────────────────
        # One int per Hanzi in original document order — physical ink density.
        stroke_count_array = [
            ZH_STROKE_COUNT.get(ch, FALLBACK_STROKE_COUNT)
            for ch in text if _is_hanzi(ch)
        ]

        # ── 3. Pinyin romanization ─────────────────────────────────────────────
        if _PYPINYIN_AVAILABLE:
            pinyin_tokens: List[str] = []
            for word in words:
                py_list = lazy_pinyin(word)
                # Filter to non-empty, normalize any stray unicode
                syllables = [
                    s.encode("ascii", "ignore").decode()
                    for s in py_list
                    if s.strip()
                ]
                if syllables:
                    pinyin_tokens.append(" ".join(syllables))
            pinyin_str = " ".join(pinyin_tokens)
        else:
            # Without pypinyin, pass the words themselves (C++ will see low alpha)
            pinyin_str = " ".join(w for w in words if w.isascii())

        # ── 4. C++ BPV on Pinyin + stroke waveform passthrough ───────────────
        if not _CPP_AVAILABLE or not pinyin_str.strip():
            return self._stroke_only_result(
                true_native_char_count, true_tokenized_word_count, stroke_count_array
            )

        n = len(pinyin_str) + 1
        # Use analyze_with_strokes if available (v3.2+) so the stroke array
        # round-trips through C++ and appears in raw_telemetry.structural_waveform.
        if hasattr(_core, "analyze_with_strokes"):
            results = _core.analyze_with_strokes(pinyin_str, n, 1, stroke_count_array)
        else:
            results = _core.analyze(pinyin_str, n, 1)

        if not results:
            return self._stroke_only_result(
                true_native_char_count, true_tokenized_word_count, stroke_count_array
            )

        win = results[0]
        rt  = win.get("raw_telemetry", {})

        # ── 5. Merge — native counts override C++ structural baseline ──────────
        return MicroResult(
            vectors=dict(win["vectors"]),
            raw={
                "total_chars":             true_native_char_count,
                "total_words":             true_tokenized_word_count,
                "avg_word_length":         round(
                    true_native_char_count / max(1, true_tokenized_word_count), 2
                ),
                "phonetic_text":           pinyin_str,
                "stroke_count_array":      stroke_count_array,
                "top_micro_chars":         rt.get("top_micro_chars", {}),
                "double_letter_anomalies": rt.get("double_letter_anomalies", {}),
            },
            language="ZH",
        )

    # ------------------------------------------------------------------
    # Fallback when C++ or pypinyin unavailable
    # ------------------------------------------------------------------

    def _stroke_only_result(
        self,
        total_chars: int,
        total_words: int,
        stroke_count_array: List[int],
    ) -> MicroResult:
        """Derive psychological vectors from stroke physics alone."""
        stroke_density = (
            sum(stroke_count_array) / len(stroke_count_array)
            if stroke_count_array else 0.0
        )
        return MicroResult(
            vectors={
                "intensity":  min(100.0, stroke_density * 8.0),
                "anxiety":    0.0,
                "attention":  min(100.0, stroke_density * 6.0),
                "emotion":    0.0,
                "agitation":  0.0,
                "complexity": min(100.0, stroke_density * 10.0),
            },
            raw={
                "total_chars":        total_chars,
                "total_words":        total_words,
                "avg_word_length":    round(total_chars / max(1, total_words), 2),
                "stroke_count_array": stroke_count_array,
            },
            language="ZH",
        )
