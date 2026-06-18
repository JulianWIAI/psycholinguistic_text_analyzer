"""
Macro-Layer Semantic Clusters — French (FR)
Exact French translations of the four base semantic cluster dictionaries.
Used by MultilingualSemanticAnalyzer when language_code == "FR".

Word lists are in lemma/base form to match spaCy's fr_core_news_sm output.
Note: spaCy lemmatizes French verbs to their infinitive form.
"""

from typing import Dict, List

FR_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "serré", "strict", "budget", "limite", "rare",
            "manque", "pénurie", "contraindre", "épuiser", "minimal",
            "réduire", "restriction", "insuffisance", "déficit", "privation",
        ],
        "abundance": [
            "fluide", "massif", "interminable", "abondance", "surplus",
            "riche", "généreux", "ample", "abondant", "richesse",
            "plein", "prospère", "profus", "débordant", "foisonner",
        ],
    },
    "power": {
        "control": [
            "gérer", "imposer", "dicter", "commander", "dominer",
            "contrôler", "diriger", "gouverner", "ordonner", "autorité",
            "mandat", "décret", "exiger", "régir", "réglementer",
        ],
        "submission": [
            "subir", "assigné", "forcer", "conformer", "céder",
            "obéir", "subordonné", "différer", "accepter", "endurer",
            "se soumettre", "dépendant", "se résigner", "se rendre", "plier",
        ],
    },
    "visibility": {
        "concealment": [
            "couche", "obscurcir", "ombre", "cacher", "dissimuler",
            "masquer", "couvrir", "voile", "supprimer", "taire",
            "enfouir", "occulter", "travestir", "camoufler", "celer",
        ],
        "exposure": [
            "lumineux", "évident", "clair", "révéler", "exposer",
            "transparent", "ouvert", "visible", "illuminer", "manifester",
            "montrer", "dévoiler", "publier", "mettre en lumière", "signaler",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "retourner", "mémoire", "racine", "tradition", "passé",
            "ancien", "restaurer", "souvenir", "nostalgie", "héritage",
            "origine", "retour", "hier", "histoire", "nostalgique",
        ],
        "future_projective": [
            "avancer", "horizon", "prochain", "futur", "avant",
            "progrès", "innover", "envisager", "prospective", "vision",
            "émergent", "demain", "planifier", "projeter", "impulser",
        ],
    },
}
