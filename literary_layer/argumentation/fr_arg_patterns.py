"""
Literary Layer — French Argumentation Patterns (Phase 7)
Mirror of en_arg_patterns.py in French.  Naming convention is identical to
both the EN and DE modules so ArgumentationDetector dispatches transparently.
"""
from __future__ import annotations
from typing import List

MIN_SCORE: int = 2

# ══════════════════════════════════════════════════════════════════════════════
# LOGOS
# ══════════════════════════════════════════════════════════════════════════════

LOGOS_CONNECTORS: frozenset = frozenset({
    "donc", "ainsi", "par conséquent", "en conséquence",
    "dès lors", "c'est pourquoi", "il s'ensuit",
})

LOGOS_EVIDENCE_WORDS: frozenset = frozenset({
    "preuve", "preuves", "données", "statistiques", "étude", "études",
    "recherche", "analyse", "résultats", "conclusions", "rapport",
    "chiffres", "pourcentage", "enquête",
})

LOGOS_CAUSAL_VERBS: frozenset = frozenset({
    "montre", "montrent", "prouve", "prouvent", "confirme", "confirment",
    "démontre", "démontrent", "indique", "indiquent", "révèle", "révèlent",
})

LOGOS_PHRASES: List[str] = [
    "par exemple", "notamment", "à titre d'exemple",
    "les données montrent", "les études montrent",
    "selon les recherches", "il en ressort que",
    "on peut conclure", "cela démontre", "cela prouve",
    "en conclusion", "en résumé", "sur la base de",
    "à la lumière de", "compte tenu de",
]

# ══════════════════════════════════════════════════════════════════════════════
# ETHOS
# ══════════════════════════════════════════════════════════════════════════════

ETHOS_AUTHORITY_WORDS: frozenset = frozenset({
    "expert", "experts", "scientifique", "scientifiques",
    "chercheur", "chercheurs", "professeur", "autorité",
    "spécialiste", "littérature", "consensus", "établi",
    "vérifié", "confirmé", "fiable", "crédible",
})

ETHOS_PHRASES: List[str] = [
    "selon", "d'après", "comme l'indique",
    "les experts s'accordent", "les scientifiques montrent",
    "il est largement admis", "il est bien établi",
    "d'après les recherches", "selon les études",
    "de mon expérience", "en tant que professionnel",
]

# ══════════════════════════════════════════════════════════════════════════════
# PATHOS
# ══════════════════════════════════════════════════════════════════════════════

PATHOS_EMOTION_WORDS: frozenset = frozenset({
    "amour", "peur", "espoir", "joie", "douleur", "chagrin", "deuil",
    "fierté", "honte", "colère", "désespoir", "bonheur", "tristesse",
    "compassion", "empathie", "souffrance", "sacrifice", "dignité",
    "justice", "liberté", "oppression", "innocent", "victime",
    "enfants", "famille", "communauté", "humanité", "courage",
})

PATHOS_INTENSIFIERS: frozenset = frozenset({
    "profondément", "terriblement", "désespérément", "passionnément",
    "bouleversant", "déchirant", "magnifique", "tragique", "urgent",
    "alarmant", "émouvant", "touchant",
})

PATHOS_PHRASES: List[str] = [
    "pensons aux enfants", "nos enfants", "nos familles",
    "pour le bien de", "nous ne pouvons pas rester indifférents",
    "le coût humain", "des vies sont en jeu",
    "personne ne devrait", "tout le monde mérite",
    "au cœur de", "profondément bouleversant",
]

# ══════════════════════════════════════════════════════════════════════════════
# ARGUMENTATIVE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

CLAIM_VERBS: frozenset = frozenset({
    "affirme", "affirment", "soutiens", "soutient", "prétends",
    "prétend", "propose", "maintiens", "maintient", "soutiens",
})

CLAIM_OPENERS: List[str] = [
    "je crois", "je soutiens", "j'affirme", "je maintiens",
    "nous croyons", "il est clair que", "il est évident que",
    "sans aucun doute", "il ne fait aucun doute",
    "il faut", "on doit", "nous devons",
]

PREMISE_MARKERS: frozenset = frozenset({
    "parce que", "car", "puisque", "étant donné",
    "vu que", "attendu que",
})

PREMISE_PHRASES: List[str] = [
    "pour la raison que", "étant donné que", "à la lumière de",
    "en raison de", "du fait de", "compte tenu de",
]

EVIDENCE_PHRASES: List[str] = [
    "par exemple", "notamment", "comme le montre",
    "selon", "d'après", "les études montrent",
    "à titre d'illustration", "tel est le cas de",
]
