"""
spaCy Model Registry
Loads and caches spaCy models by name.
All language analyzers retrieve models through this registry so each
model is loaded at most once per process lifetime.

Model → package dependencies:
    en_core_web_sm     — pip install spacy && python -m spacy download en_core_web_sm
    es_core_news_sm    — python -m spacy download es_core_news_sm
    fr_core_news_sm    — python -m spacy download fr_core_news_sm
    ja_core_news_sm    — pip install fugashi ipadic && python -m spacy download ja_core_news_sm
"""

from typing import Dict
import spacy


class ModelRegistry:
    """Thread-safe (GIL-protected) singleton cache for loaded spaCy models."""

    _cache: Dict[str, spacy.Language] = {}

    @classmethod
    def load(cls, model_name: str) -> spacy.Language:
        """
        Return a cached spaCy model, loading it on first access.

        Raises RuntimeError with install instructions if the model is missing.
        """
        if model_name not in cls._cache:
            try:
                cls._cache[model_name] = spacy.load(model_name)
            except OSError:
                install_cmd = cls._install_hint(model_name)
                raise RuntimeError(
                    f"spaCy model '{model_name}' is not installed.\n"
                    f"Install it with:\n    {install_cmd}"
                )
        return cls._cache[model_name]

    @staticmethod
    def _install_hint(model_name: str) -> str:
        hints = {
            "en_core_web_sm": "python -m spacy download en_core_web_sm",
            "es_core_news_sm": "python -m spacy download es_core_news_sm",
            "fr_core_news_sm": "python -m spacy download fr_core_news_sm",
            "ja_core_news_sm": (
                "pip install fugashi ipadic && "
                "python -m spacy download ja_core_news_sm"
            ),
        }
        return hints.get(model_name, f"python -m spacy download {model_name}")

    @classmethod
    def loaded_models(cls) -> list:
        """List currently cached model names (useful for health checks)."""
        return list(cls._cache.keys())
