"""
Literary Layer — French Semantic Field Seed Words (Phase 3)
Mirror of en_fields.py in French for use with fr_core_news_md.

Words are in their dictionary/lemma form.  The FieldScorer looks up each
seed word in the spaCy French vocabulary to build centroid vectors.
"""
from __future__ import annotations
from typing import Dict, List

FR_FIELDS: Dict[str, List[str]] = {

    "ANIMALS": [
        "cheval", "chien", "chat", "oiseau", "poisson", "loup", "ours",
        "cerf", "lion", "tigre", "aigle", "renard", "lapin", "serpent",
        "baleine", "dauphin", "corbeau", "souris", "hibou", "faucon",
        "bête", "proie", "troupeau", "plume", "patte", "fourrure",
        "griffe", "bec", "crinière", "queue",
    ],

    "FOOD": [
        "faim", "manger", "festin", "goût", "cuire", "saveur", "repas",
        "pain", "boire", "vin", "fruit", "doux", "amer", "sel",
        "épice", "récolte", "nourrir", "appétit", "affamer", "dévorer",
        "savourer", "grain", "viande", "soupe", "rôtir", "recette",
        "cuisine", "banquet",
    ],

    "NATURE": [
        "arbre", "forêt", "rivière", "montagne", "ciel", "nuage",
        "feuille", "pierre", "racine", "fleur", "pluie", "vent",
        "terre", "soleil", "lune", "étoile", "océan", "lac", "herbe",
        "prairie", "vallée", "falaise", "rivage", "ruisseau", "aube",
        "crépuscule", "sauvage", "colline", "brouillard", "neige",
    ],

    "TRAVEL": [
        "voyage", "route", "chemin", "arriver", "partir", "navire",
        "errer", "pèlerin", "destination", "étranger", "horizon",
        "carte", "boussole", "retourner", "carrefour", "passage",
        "lointain", "migrer", "chercher", "aventure", "quête",
        "départ", "expédition", "caravane", "voyageur",
    ],

    "WAR": [
        "bataille", "arme", "épée", "soldat", "combattre", "blessure",
        "ennemi", "armée", "siège", "conquérir", "défaite", "sang",
        "canon", "fusil", "marcher", "troupe", "commandant", "forteresse",
        "reddition", "attaque", "victoire", "guerrier", "bouclier",
        "flèche", "guerre", "combat", "front",
    ],

    "BODY": [
        "coeur", "main", "oeil", "visage", "souffle", "sang", "peau",
        "os", "muscle", "gorge", "épaule", "poitrine", "bras", "jambe",
        "pied", "tête", "oreille", "nez", "bouche", "lèvre", "langue",
        "doigt", "larme", "sueur", "pouls", "front",
    ],

    "HOME": [
        "maison", "chambre", "porte", "fenêtre", "famille", "abri",
        "foyer", "nid", "chaleur", "confort", "repos", "cuisine",
        "lit", "toit", "mur", "table", "chaise", "bienvenue", "retour",
        "appartenir", "enfance", "souvenir", "seuil", "demeure",
    ],

    "DEATH": [
        "mourir", "tombe", "funérailles", "pleurer", "fantôme",
        "éternel", "déclin", "cendre", "poussière", "enterrement",
        "cercueil", "mort", "cadavre", "veuve", "deuil", "perte",
        "finir", "disparaître", "ombre", "obscurité", "silence",
        "périr", "élégie",
    ],

    "LOVE": [
        "coeur", "baiser", "étreinte", "tendre", "désir", "chérir",
        "adorer", "bien-aimé", "passion", "dévotion", "affection",
        "romance", "fidèle", "loyal", "lien", "beauté", "douceur",
        "chaleur", "intime", "ravissement", "serment", "soupir",
    ],

    "POWER": [
        "autorité", "commander", "régner", "obéir", "couronne",
        "trône", "dominer", "contrôler", "maître", "serviteur",
        "roi", "reine", "gouverner", "loi", "force", "puissance",
        "volonté", "empire", "tyran", "noble", "seigneur", "décret",
    ],

    "RELIGION": [
        "prière", "sacré", "divin", "âme", "foi", "saint", "église",
        "dieu", "ciel", "ange", "esprit", "rituel", "miracle",
        "péché", "grâce", "temple", "prêtre", "bénédiction",
        "paradis", "éternel", "rédemption", "alliance", "écriture",
        "prophète", "pèlerinage",
    ],

    "MONEY": [
        "dette", "richesse", "payer", "coût", "commerce", "pauvreté",
        "pièce", "or", "argent", "marchand", "marché", "acheter",
        "vendre", "profit", "perte", "fortune", "trésor", "joyau",
        "banque", "prix", "économie", "impôt",
    ],

    "SCIENCE": [
        "expérience", "théorie", "mesurer", "observer", "découvrir",
        "hypothèse", "données", "élément", "atome", "force", "énergie",
        "calculer", "laboratoire", "recherche", "preuve", "test",
        "analyse", "équation", "méthode", "logique", "raison",
        "fait", "principe", "gravité",
    ],

    "TIME": [
        "moment", "mémoire", "passé", "avenir", "âge", "heure",
        "aube", "siècle", "jour", "nuit", "année", "saison",
        "changer", "passer", "couler", "attendre", "bref", "éternel",
        "jadis", "maintenant", "rester", "jeunesse", "vieillesse",
        "ancien", "instant", "fugace",
    ],
}
