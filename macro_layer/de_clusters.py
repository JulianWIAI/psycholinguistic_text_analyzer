"""
Macro-Layer Semantic Clusters — German (DE)
6-cluster operational/steganographic dictionaries.
Words are in lemma/base form to match spaCy de_core_news_sm output.
Verbs in infinitive form; nouns in nominative singular.
"""

from typing import Dict, List

DE_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "rationieren", "Defizit", "Hungersnot", "streng", "drosseln",
            "knapp", "Mangel", "einschränken", "erschöpfen", "minimal",
            "entbehren", "Austerität", "einfrieren", "Kürzung", "entziehen",
            "verknappen", "begrenzen", "Budget", "ausquetschen", "Erschöpfung",
            "belasten", "austrocknen", "Unzulänglichkeit", "mager", "würgen",
        ],
        "abundance": [
            "Überschuss", "überschwemmen", "üppig", "unbegrenzt", "Vermögen",
            "Reichtum", "überquellen", "großzügig", "reichlich", "wohlhabend",
            "florieren", "profus", "Überfluss", "Verschwendung", "opulent",
            "Schatz", "fließen", "gedeihen", "sättigen", "massiv",
            "trömen", "bereichern", "strotzend", "Fülle", "exuberant",
        ],
    },
    "power": {
        "control": [
            "erzwingen", "diktieren", "ermächtigen", "Raster", "einsetzen",
            "befehlen", "dominieren", "regieren", "Mandat", "Überwachung",
            "zwingen", "verpflichten", "überwachen", "regulieren", "außer Kraft setzen",
            "eindämmen", "ausnutzen", "verwalten", "steuern", "herrschen",
            "unterdrücken", "ausführen", "kanalisieren", "sperren", "kontrollieren",
        ],
        "submission": [
            "ertragen", "zugewiesen", "gezwungen", "mitreißen", "nachgeben",
            "einhalten", "unterwerfen", "gehorchen", "unterordnen", "aufschieben",
            "akzeptieren", "kapitulieren", "übergeben", "dulden", "erliegen",
            "resignieren", "einsperren", "fallen", "Druck", "hilflos",
            "erleiden", "aufnehmen", "nachgeben", "gefangen", "untertan",
        ],
    },
    "visibility": {
        "concealment": [
            "verschleiern", "abfangen", "Schleier", "verschlüsseln", "Schatten",
            "Schicht", "verbergen", "tarnen", "maskieren", "bedecken",
            "vergraben", "unterdrücken", "verdecken", "verhüllen", "camouflieren",
            "filtern", "umleiten", "blenden", "verdecken", "dämpfen",
            "versenken", "unsichtbar", "totschweigen", "heimlich", "verschweigen",
        ],
        "exposure": [
            "senden", "klar", "offensichtlich", "Oberfläche", "hell",
            "enthüllen", "aufdecken", "transparent", "offen", "sichtbar",
            "beleuchten", "manifestieren", "anzeigen", "signalisieren", "veröffentlichen",
            "offenkundig", "entlarven", "offenbaren", "erklären", "nackt",
            "explizit", "öffentlich", "preisgeben", "direkt", "aufzeigen",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "Ursprung", "wiederherstellen", "Erinnerung", "damals", "Erbe",
            "zurückkehren", "Tradition", "früher", "erinnern", "Rückblick",
            "Kulturerbe", "Herkunft", "etablieren", "Relikt", "Nostalgie",
            "zurückgewinnen", "Vorfahre", "umkehren", "Vergangenheit", "Überrest",
            "archivieren", "vergangen", "veraltet", "historisch", "Gründer",
        ],
        "future_projective": [
            "Horizont", "bevorstehend", "Fortschritt", "Bedrohung", "Trajektorie",
            "Vorankommen", "innovieren", "entstehen", "Vision", "Ziel",
            "eskalieren", "unmittelbar", "entfalten", "projizieren", "nächste",
            "ansteigen", "konvergieren", "drohen", "sammeln", "Einsetzen",
            "Prognose", "bevorstehen", "mobilisieren", "auslösen", "aufkommen",
        ],
    },
    "cognitive": {
        "scientific": [
            "berechnen", "Variable", "Physik", "Metrik", "beobachten",
            "Struktur", "analysieren", "empirisch", "Parameter", "messen",
            "quantifizieren", "modellieren", "Daten", "Hypothese", "systematisch",
            "Logik", "Formel", "experimentieren", "Evidenz", "verifizieren",
            "kalibrieren", "klassifizieren", "Präzision", "Algorithmus", "ableiten",
        ],
        "emotional": [
            "fühlen", "hoffen", "Seele", "verzweifeln", "intuitiv",
            "abstrakt", "spüren", "glauben", "träumen", "leiden",
            "trauern", "lieben", "fürchten", "schmerzen", "sehnen",
            "betrauern", "schmachten", "quälen", "vorstellen", "begehren",
            "mitfühlen", "Trauer", "Leidenschaft", "wünschen", "aufrichtig",
        ],
    },
    "kinetic": {
        "aggression": [
            "schlagen", "Durchbrechen", "kinetisch", "neutralisieren", "Angriff",
            "attackieren", "bestürmen", "vernichten", "eliminieren", "Bruch",
            "eindringen", "zerquetschen", "überwältigen", "Razzia", "zünden",
            "mobilisieren", "starten", "einsetzen", "eskalieren", "auslöschen",
            "vernichten", "beschlagnahmen", "gefangen nehmen", "treffen", "durchbrechen",
        ],
        "diplomacy": [
            "verhandeln", "pausieren", "verzögern", "Abkommen", "Gleichgewicht",
            "Waffenstillstand", "Dialog", "vermitteln", "stabilisieren", "Pause",
            "aufschieben", "versöhnen", "Kompromiss", "zurückziehen", "eindämmen",
            "überwachen", "beobachten", "aufrechterhalten", "beibehalten", "mäßigen",
            "nachgeben", "beilegen", "einigen", "befrieden", "entspannen",
        ],
    },
}
