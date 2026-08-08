"""
Literary Layer — German Semantic Field Seed Words (Phase 3)
Mirror of en_fields.py in German for use with de_core_news_md.

Words are in their dictionary/lemma form.  The FieldScorer looks up each
seed word in the spaCy German vocabulary to build centroid vectors.
"""
from __future__ import annotations
from typing import Dict, List

DE_FIELDS: Dict[str, List[str]] = {

    "ANIMALS": [
        "Pferd", "Hund", "Katze", "Vogel", "Fisch", "Wolf", "Bär",
        "Hirsch", "Löwe", "Tiger", "Adler", "Fuchs", "Hase", "Schlange",
        "Wal", "Delphin", "Krähe", "Maus", "Eule", "Falke", "Tier",
        "Beute", "Herde", "Feder", "Pfote", "Fell", "Kralle", "Schnabel",
        "Mähne", "Schwanz", "Stallion", "Stall",
    ],

    "FOOD": [
        "Hunger", "essen", "Fest", "Geschmack", "kochen", "Aroma",
        "Mahlzeit", "Brot", "trinken", "Wein", "Obst", "süß", "bitter",
        "Salz", "Gewürz", "Ernte", "nähren", "Appetit", "verschlingen",
        "genießen", "Getreide", "Fleisch", "Suppe", "braten", "Rezept",
        "Zutaten", "Schmaus", "Küche",
    ],

    "NATURE": [
        "Baum", "Wald", "Fluss", "Berg", "Himmel", "Wolke", "Blatt",
        "Stein", "Wurzel", "Blume", "Regen", "Wind", "Erde", "Sonne",
        "Mond", "Stern", "Ozean", "See", "Gras", "Wiese", "Tal",
        "Klippe", "Ufer", "Bach", "Wildnis", "Hügel", "Nebel",
        "Schnee", "Eis", "Blüte", "Dorn",
    ],

    "TRAVEL": [
        "Reise", "Weg", "Pfad", "ankommen", "abreisen", "Schiff",
        "Seereise", "wandern", "streifen", "Pilger", "Ziel", "fremd",
        "Horizont", "Karte", "Kompass", "zurückkehren", "Kreuzweg",
        "Passage", "fern", "Ausland", "Abenteuer", "Aufbruch",
        "Expedition", "Karawane", "Reisende",
    ],

    "WAR": [
        "Kampf", "Waffe", "Schwert", "Soldat", "kämpfen", "Wunde",
        "Feind", "Armee", "Belagerung", "Sieg", "Niederlage", "Blut",
        "Kanone", "Gewehr", "marschieren", "Truppe", "Festung",
        "Kapitulation", "Angriff", "Krieger", "Schild", "Pfeil",
        "Krieg", "Schlachten", "Gefangene", "Front",
    ],

    "BODY": [
        "Herz", "Hand", "Auge", "Gesicht", "Atem", "Blut", "Haut",
        "Knochen", "Muskel", "Kehle", "Schulter", "Brust", "Arm",
        "Bein", "Fuß", "Kopf", "Ohr", "Nase", "Mund", "Lippe",
        "Zunge", "Finger", "Träne", "Schweiß", "Puls", "Stirn",
    ],

    "HOME": [
        "Haus", "Zimmer", "Tür", "Fenster", "Familie", "Unterkunft",
        "Herd", "Nest", "Wärme", "Komfort", "Ruhe", "Küche", "Bett",
        "Dach", "Wand", "Tisch", "Stuhl", "Willkommen", "Heimkehr",
        "Kindheit", "Erinnerung", "Schwelle", "Hütte", "Wohnort",
    ],

    "DEATH": [
        "sterben", "Grab", "Beerdigung", "trauern", "Geist", "ewig",
        "Verfall", "Asche", "Staub", "Bestattung", "Sarg", "Tod",
        "Leiche", "Witwe", "Trauer", "Verlust", "enden", "verblassen",
        "Schatten", "Finsternis", "Stille", "vergehen", "Elegie",
    ],

    "LOVE": [
        "Herz", "Kuss", "Umarmung", "zart", "Sehnsucht", "schätzen",
        "anbeten", "Geliebte", "Leidenschaft", "Hingabe", "Zuneigung",
        "Romantik", "Begehren", "treu", "loyal", "Bindung", "Schönheit",
        "Sanftheit", "Intimität", "Verzückung", "Schwur",
    ],

    "POWER": [
        "Autorität", "Befehl", "herrschen", "gehorchen", "Krone",
        "Thron", "dominieren", "kontrollieren", "Meister", "Diener",
        "König", "Königin", "regieren", "Gesetz", "Kraft", "Stärke",
        "Wille", "Imperium", "Tyrann", "Edler", "Lehnsherr", "Dekret",
    ],

    "RELIGION": [
        "Gebet", "heilig", "göttlich", "Seele", "Glaube", "Kirche",
        "Gott", "Himmel", "Engel", "Geist", "Ritual", "Wunder",
        "Sünde", "Gnade", "Tempel", "Priester", "Segen", "Paradies",
        "Erlösung", "Bund", "Schrift", "Prophet", "Pilgerfahrt",
    ],

    "MONEY": [
        "Schulden", "Reichtum", "zahlen", "Kosten", "Handel", "Armut",
        "Münze", "Gold", "Silber", "Kaufmann", "Markt", "kaufen",
        "verkaufen", "Gewinn", "Verlust", "Vermögen", "Schatz",
        "Juwel", "Bank", "Preis", "Wirtschaft", "Steuer",
    ],

    "SCIENCE": [
        "Experiment", "Theorie", "messen", "beobachten", "entdecken",
        "Hypothese", "Daten", "Element", "Atom", "Kraft", "Energie",
        "berechnen", "Labor", "Forschung", "Beweis", "Test",
        "Analyse", "Gleichung", "Methode", "Logik", "Vernunft",
        "Tatsache", "Prinzip", "Schwerkraft",
    ],

    "TIME": [
        "Moment", "Erinnerung", "Vergangenheit", "Zukunft", "Zeitalter",
        "Stunde", "Morgenröte", "Jahrhundert", "Tag", "Nacht", "Jahr",
        "Jahreszeit", "vergehen", "fließen", "warten", "ewig",
        "einst", "verbleiben", "Jugend", "Alter", "uralt", "Augenblick",
    ],
}
