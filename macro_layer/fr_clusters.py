"""
Macro-Layer Semantic Clusters — French (FR)
6-cluster operational/steganographic dictionaries.
Words are in lemma/base form to match spaCy fr_core_news_sm output.
"""

from typing import Dict, List

FR_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "rationner", "déficit", "famine", "strict", "serré",
            "pénurie", "manque", "contraindre", "épuiser", "minimal",
            "restriction", "austérité", "gel", "coupure", "priver",
            "assécher", "restreindre", "limite", "pressurer", "déplétion",
            "grever", "tarir", "insuffisance", "maigre", "étrangler",
        ],
        "abundance": [
            "surplus", "inonder", "luxueux", "infini", "atout",
            "richesse", "déborder", "généreux", "ample", "abondant",
            "prospère", "foisonner", "profus", "excès", "gaspillage",
            "opulent", "trésor", "ruisseler", "florissant", "combler",
            "regorger", "saturer", "cascade", "surabondance", "exubérant",
        ],
    },
    "power": {
        "control": [
            "imposer", "dicter", "autoriser", "quadrillage", "déployer",
            "commander", "dominer", "gouverner", "mandat", "surveillance",
            "contraindre", "obliger", "surveiller", "réguler", "outrepasser",
            "contenir", "exploiter", "gérer", "diriger", "régner",
            "réprimer", "exécuter", "canaliser", "verrouiller", "contrôler",
        ],
        "submission": [
            "endurer", "assigné", "forcé", "emporté", "céder",
            "obéir", "soumettre", "subordonné", "différer", "accepter",
            "capituler", "rendre", "tolérer", "succomber", "résigner",
            "confiner", "piéger", "presser", "impuissant", "supporter",
            "absorber", "acquiescer", "plier", "assujettir", "subir",
        ],
    },
    "visibility": {
        "concealment": [
            "obscurcir", "intercepter", "voile", "chiffrer", "ombre",
            "couche", "cacher", "dissimuler", "masquer", "couvrir",
            "enfouir", "supprimer", "embusquer", "envelopper", "camoufler",
            "filtrer", "détourner", "aveugler", "occulter", "étouffer",
            "noyer", "invisible", "taire", "crypter", "voiler",
        ],
        "exposure": [
            "diffuser", "clair", "évident", "surface", "lumineux",
            "révéler", "exposer", "transparent", "ouvert", "visible",
            "illuminer", "manifester", "afficher", "signaler", "publier",
            "manifeste", "démasquer", "dévoiler", "déclarer", "nu",
            "explicite", "ostensible", "divulguer", "direct", "découvrir",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "racines", "restaurer", "mémoire", "avant", "héritage",
            "retourner", "tradition", "ancien", "souvenir", "rappel",
            "patrimoine", "origine", "établir", "relique", "nostalgie",
            "regagner", "ancêtre", "revenir", "passé", "vestige",
            "archiver", "révolu", "daté", "historique", "fondateur",
        ],
        "future_projective": [
            "horizon", "entrant", "avancer", "menace", "trajectoire",
            "progrès", "innover", "émerger", "vision", "cible",
            "escalader", "imminent", "déployer", "projeter", "prochain",
            "surgir", "converger", "pressentir", "rassembler", "prévision",
            "impendre", "anticiper", "mobiliser", "déclencher", "survenir",
        ],
    },
    "cognitive": {
        "scientific": [
            "calculer", "variable", "physique", "métrique", "observer",
            "structure", "analyser", "empirique", "paramètre", "mesurer",
            "quantifier", "modéliser", "données", "hypothèse", "systématique",
            "logique", "formule", "expérimenter", "preuve", "vérifier",
            "calibrer", "classer", "précision", "algorithme", "dériver",
        ],
        "emotional": [
            "sentir", "espérer", "âme", "désespoir", "intuitif",
            "abstrait", "ressentir", "croire", "rêver", "souffrir",
            "pleurer", "aimer", "craindre", "aspirer", "languir",
            "angoisser", "imaginer", "désirer", "compatir", "tristesse",
            "passion", "souhaiter", "sincère", "douleur", "nostalgie",
        ],
    },
    "kinetic": {
        "aggression": [
            "frapper", "brèche", "cinétique", "éliminer", "cible",
            "attaque", "assaut", "détruire", "neutraliser", "rupture",
            "pénétrer", "écraser", "submerger", "raid", "déclencher",
            "mobiliser", "lancer", "engager", "escalader", "anéantir",
            "saisir", "capturer", "percuter", "envahir", "abattre",
        ],
        "diplomacy": [
            "négocier", "tenir", "temporiser", "traité", "équilibre",
            "cessez-le-feu", "dialogue", "médier", "stabiliser", "pause",
            "différer", "réconcilier", "compromis", "retirer", "contenir",
            "surveiller", "observer", "soutenir", "maintenir", "retenir",
            "modérer", "concéder", "régler", "convenir", "résoudre",
        ],
    },
}
