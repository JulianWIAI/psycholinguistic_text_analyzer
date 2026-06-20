"""
Korean (KO) Semantic Cluster Definitions + KoreanSemanticAnalyzer.

300 Korean seed words: 6 clusters × 2 poles × 25 words.
Used by KoreanSemanticAnalyzer with spaCy ko_core_news_sm.

Tokenizer override: the default ko_core_news_sm tokenizer uses MeCab-Ko for
morpheme segmentation. For seed-word matching we need whole-word (eojeol)
tokens, so the tokenizer is replaced with spaCy's whitespace-based Tokenizer.
"""

from typing import Dict, List, Tuple

from macro_layer.semantic_analyzer import (
    MacroScore,
    ClusterHit,
    VectorClusterScorer,
    _load_spacy,
    extract_entity_polarity,
)

# ---------------------------------------------------------------------------
# Seed word dictionaries
# ---------------------------------------------------------------------------
KO_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "부족", "결핍", "기근", "빈곤", "희소",
            "고갈", "제한", "긴축", "부채", "결손",
            "감소", "고갈되다", "궁핍", "절약", "동결",
            "압박", "부담", "박탈", "빈곤층", "식량난",
            "자원부족", "예산삭감", "위기", "공급난", "여유없다",
        ],
        "abundance": [
            "풍부", "번영", "여유", "자원", "잉여",
            "수익", "축적", "투자", "성장", "흑자",
            "공급", "비축", "이익", "생산", "자산",
            "확장", "소득", "보유", "역량", "재원",
            "흥청망청", "풍요", "넉넉하다", "증가", "충족",
        ],
    },
    "power": {
        "control": [
            "통제", "지배", "권력", "명령", "강제",
            "규제", "관리", "독점", "억압", "감시",
            "지휘", "조종", "강요", "집권", "장악",
            "지시", "통치", "봉쇄", "탄압", "권위",
            "독재", "검열", "강경", "제재", "집행",
        ],
        "submission": [
            "복종", "굴복", "순응", "허용", "승인",
            "체념", "굴종", "양보", "포기", "수용",
            "타협", "굴욕", "복속", "종속", "의존",
            "수동", "묵인", "승복", "항복", "패배",
            "굴하다", "따르다", "순종", "복속되다", "양도",
        ],
    },
    "visibility": {
        "concealment": [
            "은폐", "비밀", "숨기다", "위장", "암호",
            "은닉", "가면", "불투명", "익명", "위조",
            "허위", "기만", "정보차단", "침묵", "내부정보",
            "잠복", "위장공작", "분장", "흑막", "비공개",
            "차단", "가리다", "감추다", "내막", "보안",
        ],
        "exposure": [
            "폭로", "공개", "발각", "투명", "공표",
            "발표", "보도", "인지", "추적", "확인",
            "유출", "내부고발", "증거", "조사", "노출",
            "공시", "알리다", "공인", "적발", "밝히다",
            "드러나다", "해명", "증언", "고발", "보고",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "역사", "전통", "유산", "과거", "기원",
            "조상", "고대", "뿌리", "민족", "문화유산",
            "기억", "귀향", "정체성", "계승", "세대",
            "추억", "고향", "선조", "옛날", "발상지",
            "유물", "복고", "향수", "전래", "사적",
        ],
        "future_projective": [
            "미래", "전망", "계획", "목표", "발전",
            "혁신", "도약", "확장", "준비", "전략",
            "대비", "진전", "예측", "투사", "청사진",
            "가속", "동원", "도전", "진보", "비전",
            "위협", "에스컬레이션", "행동", "다가오다", "결전",
        ],
    },
    "cognitive": {
        "scientific": [
            "분석", "데이터", "모델", "가설", "측정",
            "알고리즘", "논리", "정밀", "방법론", "증명",
            "지표", "변수", "시스템", "분류", "실험",
            "계산", "확률", "통계", "수식", "접근법",
            "추론", "시뮬레이션", "처리", "평가", "결과",
        ],
        "emotional": [
            "감정", "영혼", "고통", "희망", "두려움",
            "사랑", "슬픔", "그리움", "양심", "직관",
            "분노", "자비", "신앙", "소망", "감성",
            "불안", "기쁨", "정서", "마음", "영감",
            "절망", "친절", "아쉬움", "걱정", "아픔",
        ],
    },
    "kinetic": {
        "aggression": [
            "공격", "충돌", "파괴", "침략", "습격",
            "폭격", "표적", "테러", "포위", "붕괴",
            "폭발", "격화", "동원", "대결", "점령",
            "전쟁", "교전", "살상", "도발", "침입",
            "전투", "약탈", "발사", "총격", "강경대응",
        ],
        "diplomacy": [
            "협상", "평화", "휴전", "대화", "중재",
            "합의", "타결", "안정", "화해", "정상화",
            "철수", "완화", "조약", "성명", "선언",
            "외교", "협력", "승인", "교류", "참여",
            "조정", "긴장완화", "보장", "공약", "연합",
        ],
    },
}


# ---------------------------------------------------------------------------
# Semantic Analyzer
# ---------------------------------------------------------------------------

class KoreanSemanticAnalyzer:
    """
    Macro-layer semantic analyzer for Korean.

    Uses spaCy ko_core_news_sm with a whitespace-based tokenizer override so
    that seed words match against whole eojeol (syllabic words) rather than
    MeCab morphemes. VectorClusterScorer provides vector similarity fallback
    when the model supports it.
    """

    def __init__(self) -> None:
        from spacy.tokenizer import Tokenizer

        self._nlp = _load_spacy("ko_core_news_sm")

        # Replace morpheme tokenizer with whitespace tokenizer for whole-word matching
        self._nlp.tokenizer = Tokenizer(self._nlp.vocab)

        # Ensure sentence boundaries are available for entity polarity extraction
        _SENT_COMPONENTS = ("parser", "senter", "sentencizer")
        if not any(self._nlp.has_pipe(p) for p in _SENT_COMPONENTS):
            self._nlp.add_pipe("sentencizer")

        self._lookup = self._build_lookup()
        self._scorer = VectorClusterScorer(
            nlp=self._nlp,
            clusters=KO_CLUSTERS,
            exact_lookup=self._lookup,
        )

    def _build_lookup(self) -> Dict[str, Tuple[str, str, float]]:
        lookup: Dict[str, Tuple[str, str, float]] = {}
        for cluster, poles in KO_CLUSTERS.items():
            for pole, words in poles.items():
                for w in words:
                    lookup[w.lower()] = (cluster, pole, 1.0)
        return lookup

    def analyze(self, text: str) -> MacroScore:
        doc = self._nlp(text)
        content_tokens = [t for t in doc if not t.is_space and not t.is_punct]
        total_words = max(1, len(content_tokens))

        raw, hits = self._scorer.score_tokens(content_tokens)

        normalized: Dict[str, Dict[str, float]] = {
            cluster: {
                pole: score / total_words
                for pole, score in poles.items()
            }
            for cluster, poles in raw.items()
        }

        entity_polarity_map = extract_entity_polarity(doc, self._scorer)

        return MacroScore(
            cluster_scores=normalized,
            total_words=total_words,
            hits=hits,
            entity_polarity_map=entity_polarity_map,
        )
