"""
Literary Layer — German Argumentation Patterns (Phase 7)
Mirror of en_arg_patterns.py in German.  All constants follow the same naming
convention so the ArgumentationDetector can consume either module transparently.

German argumentation has some language-specific features:
    • Logical connectors appear as single words (deshalb, daher, folglich).
    • Pathos vocabulary is augmented by German emotional register (Leid, Würde).
    • Ethos markers include typical academic hedging (laut, gemäß, nach).
    • Claim markers use Modal verbs (muss, sollte, darf) for normative claims.
"""
from __future__ import annotations
from typing import List

# ── Minimum score for a sentence to be classified ─────────────────────────────
MIN_SCORE: int = 2

# ══════════════════════════════════════════════════════════════════════════════
# LOGOS
# ══════════════════════════════════════════════════════════════════════════════

LOGOS_CONNECTORS: frozenset = frozenset({
    "deshalb", "daher", "folglich", "infolgedessen", "demnach",
    "somit", "mithin", "ergo",
})

LOGOS_EVIDENCE_WORDS: frozenset = frozenset({
    "Beweis", "Beweise", "Daten", "Statistik", "Studie", "Studien",
    "Forschung", "Untersuchung", "Analyse", "Ergebnisse", "Befunde",
    "Nachweis", "Belege", "Bericht", "Zahlen", "Prozent",
    # lowercased aliases for case-insensitive matching
    "beweis", "beweise", "daten", "statistik", "studie", "studien",
    "forschung", "untersuchung", "analyse", "ergebnisse", "befunde",
})

LOGOS_CAUSAL_VERBS: frozenset = frozenset({
    "zeigt", "belegt", "beweist", "bestätigt", "zeigen", "belegen",
    "beweisen", "bestätigen", "ergibt", "ergeben", "folgt", "impliziert",
})

LOGOS_PHRASES: List[str] = [
    "zum Beispiel", "beispielsweise", "zum einen",
    "laut Studien", "Forschungen zeigen", "Daten zeigen",
    "wie gezeigt wurde", "wie belegt wird",
    "als Beweis dafür", "dies beweist", "dies zeigt",
    "daraus folgt", "als Ergebnis", "infolge dessen",
    "auf der Grundlage", "auf Basis von",
]

# ══════════════════════════════════════════════════════════════════════════════
# ETHOS
# ══════════════════════════════════════════════════════════════════════════════

ETHOS_AUTHORITY_WORDS: frozenset = frozenset({
    "Experte", "Experten", "Wissenschaftler", "Forscher", "Gelehrter",
    "Professor", "Autorität", "Fachmann", "Fachleute",
    "Studie", "Literatur", "Konsens", "belegt", "bestätigt",
    "anerkannt", "verlässlich", "glaubwürdig",
    # lowercased
    "experte", "experten", "wissenschaftler", "forscher", "professor",
    "autorität", "fachmann", "fachleute", "anerkannt",
})

ETHOS_PHRASES: List[str] = [
    "laut", "gemäß", "nach Angaben von", "nach Aussage von",
    "Experten sind sich einig", "Wissenschaftler zeigen",
    "es ist allgemein anerkannt", "wie allgemein bekannt",
    "in der Wissenschaft", "laut Forschung", "nach aktuellen Studien",
    "aus meiner Erfahrung", "als Fachmann",
]

# ══════════════════════════════════════════════════════════════════════════════
# PATHOS
# ══════════════════════════════════════════════════════════════════════════════

PATHOS_EMOTION_WORDS: frozenset = frozenset({
    "Liebe", "Angst", "Hoffnung", "Freude", "Schmerz", "Trauer",
    "Stolz", "Scham", "Wut", "Verzweiflung", "Glück", "Leid",
    "Mitgefühl", "Empathie", "Würde", "Gerechtigkeit", "Freiheit",
    "Unterdrückung", "Unschuld", "Opfer", "Familie", "Kinder",
    "Gemeinschaft", "Menschlichkeit", "Mut", "Tragödie",
    # lowercased
    "liebe", "angst", "hoffnung", "freude", "schmerz", "trauer",
    "stolz", "scham", "wut", "verzweiflung", "glück", "leid",
    "mitgefühl", "empathie", "würde", "gerechtigkeit", "freiheit",
    "opfer", "familie", "kinder", "gemeinschaft", "menschlichkeit",
})

PATHOS_INTENSIFIERS: frozenset = frozenset({
    "tief", "zutiefst", "erschütternd", "bewegend", "herzzerreißend",
    "entsetzlich", "wunderschön", "tragisch", "dringend", "überwältigend",
    "erschreckend", "leidenschaftlich",
})

PATHOS_PHRASES: List[str] = [
    "denken wir an die Kinder", "unsere Kinder", "unsere Familien",
    "um des Willens", "wir können nicht wegschauen",
    "das menschliche Leid", "Leben stehen auf dem Spiel",
    "niemand sollte", "jeder verdient",
]

# ══════════════════════════════════════════════════════════════════════════════
# ARGUMENTATIVE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

CLAIM_VERBS: frozenset = frozenset({
    "argumentiere", "behaupte", "behaupten", "behauptet",
    "vertreten", "verteidige", "glaube", "meine",
    "schlage vor", "fordere", "bestehe",
})

CLAIM_OPENERS: List[str] = [
    "ich glaube", "ich argumentiere", "ich behaupte", "ich meine",
    "wir glauben", "es ist klar", "es ist offensichtlich",
    "zweifellos", "ohne Zweifel", "es steht fest",
    "man muss", "wir müssen", "es ist notwendig",
]

PREMISE_MARKERS: frozenset = frozenset({
    "weil", "da", "denn", "angesichts", "vorausgesetzt",
})

PREMISE_PHRASES: List[str] = [
    "aus dem Grund", "angesichts der Tatsache", "da dies der Fall ist",
    "in Anbetracht", "auf Grundlage", "aufgrund von",
    "unter Berücksichtigung",
]

EVIDENCE_PHRASES: List[str] = [
    "zum Beispiel", "beispielsweise", "wie gezeigt",
    "laut", "gemäß", "nach", "Forschungen zeigen",
    "als Beispiel", "zur Illustration", "wie im Fall von",
]
