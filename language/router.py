"""
Language Router
Central factory that maps a language_code string to the correct pair of
micro-layer and macro-layer analyzer instances.

Supported codes:
    "EN"  — English  (Latin BPV, spaCy en_core_web_sm)
    "ES"  — Spanish  (Latin BPV + RR/LL overrides, es_core_news_sm)
    "FR"  — French   (Latin BPV + silent terminal override, fr_core_news_sm)
    "JA"  — Japanese (Logographic matrix + Keigo, ja_core_news_sm)

All instances are cached after first construction so spaCy models are
loaded only once per process.
"""

from typing import Any, Dict

from micro_layer.base_analyzer import BaseMicroAnalyzer


# Supported language codes and their human-readable names
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "EN": "English",
    "ES": "Spanish",
    "FR": "French",
    "JA": "Japanese",
}


class LanguageRouter:
    """
    Factory + cache for language-specific analyzer pairs.

    Usage:
        router = LanguageRouter()
        micro  = router.micro("JA")
        macro  = router.macro("JA")
        result = micro.analyze(window_text)
    """

    def __init__(self):
        self._micro_cache: Dict[str, BaseMicroAnalyzer] = {}
        self._macro_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def micro(self, language_code: str) -> BaseMicroAnalyzer:
        """Return the micro-layer analyzer for *language_code*."""
        code = self._validate(language_code)
        if code not in self._micro_cache:
            self._micro_cache[code] = self._build_micro(code)
        return self._micro_cache[code]

    def macro(self, language_code: str) -> Any:
        """Return the macro-layer analyzer for *language_code*."""
        code = self._validate(language_code)
        if code not in self._macro_cache:
            self._macro_cache[code] = self._build_macro(code)
        return self._macro_cache[code]

    # ------------------------------------------------------------------
    # Private builders (lazy — only called on first access per code)
    # ------------------------------------------------------------------

    def _build_micro(self, code: str) -> BaseMicroAnalyzer:
        if code == "EN":
            from micro_layer.orthographic_analyzer import OrthographicAnalyzer
            return OrthographicAnalyzer()

        if code == "ES":
            from micro_layer.es_analyzer import SpanishOrthographicAnalyzer
            return SpanishOrthographicAnalyzer()

        if code == "FR":
            from micro_layer.fr_analyzer import FrenchOrthographicAnalyzer
            return FrenchOrthographicAnalyzer()

        if code == "JA":
            from micro_layer.ja_analyzer import JapaneseLogographicAnalyzer
            return JapaneseLogographicAnalyzer()

        raise ValueError(f"No micro analyzer registered for language code: {code!r}")

    def _build_macro(self, code: str) -> Any:
        if code == "EN":
            from macro_layer.semantic_analyzer import SemanticAnalyzer
            return SemanticAnalyzer()

        if code == "ES":
            from macro_layer.multilingual_analyzer import MultilingualSemanticAnalyzer
            from macro_layer.es_clusters import ES_CLUSTERS
            return MultilingualSemanticAnalyzer("es_core_news_sm", ES_CLUSTERS)

        if code == "FR":
            from macro_layer.multilingual_analyzer import MultilingualSemanticAnalyzer
            from macro_layer.fr_clusters import FR_CLUSTERS
            return MultilingualSemanticAnalyzer("fr_core_news_sm", FR_CLUSTERS)

        if code == "JA":
            from macro_layer.ja_clusters import JapaneseSemanticAnalyzer
            return JapaneseSemanticAnalyzer()

        raise ValueError(f"No macro analyzer registered for language code: {code!r}")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(code: str) -> str:
        upper = code.strip().upper()
        if upper not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language code: {code!r}. "
                f"Supported: {list(SUPPORTED_LANGUAGES.keys())}"
            )
        return upper
