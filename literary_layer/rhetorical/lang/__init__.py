"""
Language-specific pattern constants for the rhetorical detectors (Phase 5).

Each language has its own pattern module (en_patterns, de_patterns, fr_patterns)
that exposes the same public names (VOWELS, SKIP_POS_ALLITERATION, INTERROGATIVES,
SIMILE_PARTICLES, AS_AS_RE, CONTRASTIVE_CONJ, POLYSYNDETON_CONJ, EXCERPT_MAX …).

Detectors call get_patterns(language) to obtain the right module and access
constants through it — no detector imports a language module directly.
"""
from literary_layer.rhetorical.lang import en_patterns
from literary_layer.rhetorical.lang import de_patterns
from literary_layer.rhetorical.lang import fr_patterns

# Registry mapping ISO codes to their pattern modules
_REGISTRY = {
    "EN": en_patterns,
    "DE": de_patterns,
    "FR": fr_patterns,
}


def get_patterns(language: str):
    """
    Return the pattern module for *language*, falling back to en_patterns
    for any unsupported language code.

    Args:
        language: ISO language code ("EN", "DE", "FR", …).

    Returns:
        One of en_patterns / de_patterns / fr_patterns.
    """
    return _REGISTRY.get(language, en_patterns)
