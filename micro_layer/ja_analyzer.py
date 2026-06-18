"""
MODULE 2-JA — Japanese Logographic Micro-Layer
Completely replaces the Latin BPV matrix with a script-ratio and stroke-density
approach suited to the three Japanese writing systems.

Vector mapping:
    Kanji     → intensity + attention  (Power / Constraint — formal, heavy)
    Hiragana  → emotion                (Emotion / Fluidity — native, intimate)
    Katakana  → agitation              (Agitation / Foreignness — borrowed, disruptive)
    Stroke density (Kanji) → complexity  (Conceptual Weight / Concealment)

Character range references:
    Kanji    : U+4E00–U+9FFF  (CJK Unified Ideographs)
    Hiragana : U+3040–U+309F
    Katakana : U+30A0–U+30FF
    Latin    : ignored in logographic scoring
"""

import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List

from micro_layer.base_analyzer import BaseMicroAnalyzer, MicroResult


# ---------------------------------------------------------------------------
# Kanji stroke-count lookup table (common Joyo kanji)
# Source: JIS X 0208 stroke-count reference + common Joyo corpus
# Unknown kanji fall back to FALLBACK_STROKE_COUNT.
# ---------------------------------------------------------------------------
STROKE_COUNT: Dict[str, int] = {
    # Numbers / units
    "一": 1, "二": 2, "三": 3, "四": 5, "五": 4, "六": 4, "七": 2, "八": 2,
    "九": 2, "十": 2, "百": 6, "千": 3, "万": 3, "円": 4,
    # Time
    "年": 6, "月": 4, "日": 4, "時": 10, "分": 4, "秒": 9, "週": 11,
    # People / body
    "人": 2, "口": 3, "目": 5, "手": 4, "足": 7, "心": 4, "体": 7, "頭": 16,
    "耳": 6, "鼻": 14, "顔": 18, "首": 9, "腕": 12, "指": 9,
    # Nature
    "山": 3, "川": 3, "海": 9, "空": 8, "木": 4, "花": 7, "火": 4, "水": 4,
    "土": 3, "金": 8, "雨": 8, "雪": 11, "風": 9, "岩": 8, "石": 5,
    "草": 9, "森": 12, "林": 8,
    # Size / quality
    "大": 3, "小": 3, "高": 10, "低": 7, "長": 8, "短": 12, "広": 5,
    "狭": 9, "多": 6, "少": 4, "強": 11, "弱": 10, "重": 9, "軽": 12,
    "新": 13, "古": 5, "若": 8, "老": 6,
    # Direction / position
    "東": 8, "西": 6, "南": 9, "北": 5, "上": 3, "下": 3, "左": 5,
    "右": 5, "中": 4, "外": 5, "前": 9, "後": 9, "横": 15,
    # Place / society
    "国": 8, "市": 5, "町": 7, "村": 7, "家": 10, "部": 11, "室": 9,
    # School / communication
    "学": 8, "校": 10, "生": 5, "先": 6, "友": 4, "達": 12, "語": 14,
    "文": 4, "字": 6, "声": 7,
    # Actions
    "読": 14, "書": 10, "話": 13, "聞": 14, "見": 7, "食": 9, "飲": 12,
    "行": 6, "来": 7, "帰": 10, "思": 9, "考": 6, "知": 8, "解": 13,
    "覚": 12, "忘": 7, "使": 8, "作": 7, "開": 12, "閉": 11, "入": 2,
    "出": 5, "買": 12, "売": 7, "持": 9,
    # Colors
    "白": 5, "黒": 11, "赤": 7, "青": 8, "色": 6,
    # Power / governance (high score → concealment / complexity)
    "政": 9, "府": 8, "権": 15, "力": 2, "命": 8, "令": 5, "法": 8,
    "律": 9, "管": 14, "理": 11, "制": 8, "度": 9, "規": 11, "則": 9,
    "約": 9, "束": 7, "支": 4, "配": 10, "従": 10, "服": 8, "属": 12,
    # Concealment / revelation
    "隠": 14, "秘": 10, "密": 11, "影": 15, "暗": 13,
    "明": 8, "示": 5, "公": 4, "表": 8, "現": 11,
    # Work / society
    "仕": 5, "事": 8, "会": 6, "社": 7, "電": 13,
    # Family
    "子": 3, "女": 3, "男": 7, "兄": 5, "姉": 8, "弟": 7, "妹": 8,
    "父": 4, "母": 5,
    # Emotions / psychology
    "好": 6, "嫌": 13, "楽": 13, "苦": 8, "愛": 13, "怒": 9,
    "悲": 12, "喜": 12, "恐": 10,
    # Temporal
    "過": 12, "去": 5, "往": 8, "旧": 5, "記": 10, "憶": 16,
    "伝": 6, "統": 12, "未": 5, "来": 7, "将": 10, "進": 11,
    "展": 10, "望": 11, "希": 7,
    # Misc high-frequency
    "気": 6, "名": 6, "今": 4, "早": 6, "速": 10, "近": 7, "遠": 13,
    "自": 6, "由": 5, "主": 5, "独": 9, "立": 5,
}

FALLBACK_STROKE_COUNT: int = 8  # average for unknown kanji


# ---------------------------------------------------------------------------
# Unicode character type helpers
# ---------------------------------------------------------------------------

def _is_kanji(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _is_hiragana(ch: str) -> bool:
    return "\u3040" <= ch <= "\u309f"


def _is_katakana(ch: str) -> bool:
    return "\u30a0" <= ch <= "\u30ff"


def _is_cjk_punctuation(ch: str) -> bool:
    """Exclude punctuation from the script count (whitespace, 。、 etc.)."""
    cat = unicodedata.category(ch)
    return cat.startswith("P") or cat.startswith("Z")


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class JapaneseLogographicAnalyzer(BaseMicroAnalyzer):
    """
    Japanese micro-layer analyzer.

    Computes four raw ratios from the script composition of a window:
        kanji_ratio     → intensity + attention (Power / Constraint)
        hiragana_ratio  → emotion               (Emotion / Fluidity)
        katakana_ratio  → agitation             (Agitation / Foreignness)
        stroke_density  → complexity            (Logographic Weight)

    anxiety is left at 0.0 — it is captured by the Keigo analysis in the
    macro layer (high Keigo submission = low surface anxiety, yet high
    psycholinguistic distance).
    """

    @property
    def language_code(self) -> str:
        return "JA"

    def analyze(self, text: str) -> MicroResult:
        counts = self._count_scripts(text)
        total   = counts["total"]
        kanji   = counts["kanji"]
        hira    = counts["hiragana"]
        kata    = counts["katakana"]

        kanji_ratio  = kanji / total  if total else 0.0
        hira_ratio   = hira  / total  if total else 0.0
        kata_ratio   = kata  / total  if total else 0.0

        stroke_density = self._mean_stroke_count(text)

        vectors = {
            "intensity":   kanji_ratio   * 100,   # Kanji density as power signal
            "anxiety":     0.0,                    # Handled in macro (Keigo)
            "attention":   kanji_ratio   * 80,     # Kanji also marks formal attention
            "emotion":     hira_ratio    * 100,    # Hiragana = intimate / emotional
            "agitation":   kata_ratio    * 100,    # Katakana = foreign / disruptive
            "complexity":  stroke_density,         # Mean logographic weight
        }

        raw = {
            "total_chars":     total,
            "kanji_count":     kanji,
            "hiragana_count":  hira,
            "katakana_count":  kata,
            "kanji_ratio":     round(kanji_ratio, 4),
            "hiragana_ratio":  round(hira_ratio, 4),
            "katakana_ratio":  round(kata_ratio, 4),
            "stroke_density":  round(stroke_density, 2),
        }

        return MicroResult(vectors=vectors, raw=raw, language="JA")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _count_scripts(self, text: str) -> Dict[str, int]:
        kanji = hira = kata = total = 0
        for ch in text:
            if _is_cjk_punctuation(ch) or ch in (" ", "\n", "\t"):
                continue
            total += 1
            if _is_kanji(ch):
                kanji += 1
            elif _is_hiragana(ch):
                hira += 1
            elif _is_katakana(ch):
                kata += 1
        return {"total": total, "kanji": kanji, "hiragana": hira, "katakana": kata}

    def _mean_stroke_count(self, text: str) -> float:
        """
        Average stroke count of all Kanji characters in *text*.
        Falls back to FALLBACK_STROKE_COUNT for unknown characters.
        """
        counts: List[int] = [
            STROKE_COUNT.get(ch, FALLBACK_STROKE_COUNT)
            for ch in text if _is_kanji(ch)
        ]
        return sum(counts) / len(counts) if counts else 0.0
