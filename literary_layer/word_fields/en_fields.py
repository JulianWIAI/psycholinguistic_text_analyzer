"""
Literary Layer — English Semantic Field Seed Words (Phase 3)
14 thematic domain fields, each seeded with ~30 lemma-form words.

These seeds are passed to FieldScorer which computes a centroid vector
by averaging spaCy word vectors, then scores every content token in the
window by cosine similarity against each centroid.

Design notes:
    • Seeds are lemma-form (uninflected) so "horses" matches via lemma "horse".
    • Aim for semantic breadth within each field: include both common words and
      field-specific vocabulary so the centroid sits accurately in the domain.
    • Avoid seed words that are strongly ambiguous across multiple fields
      (e.g. "fire" belongs to HOME, NATURE, and WAR — omit or place carefully).
    • Fields are extended with DE/FR equivalents in de_fields.py / fr_fields.py.
"""
from __future__ import annotations
from typing import Dict, List

EN_FIELDS: Dict[str, List[str]] = {

    "ANIMALS": [
        "horse", "dog", "cat", "bird", "fish", "wolf", "bear", "deer",
        "lion", "tiger", "eagle", "fox", "rabbit", "snake", "whale",
        "dolphin", "crow", "mouse", "owl", "hawk", "beast", "prey",
        "herd", "flock", "pack", "feather", "paw", "fur", "claw",
        "beak", "mane", "tail", "veterinarian", "saddle", "stable",
    ],

    "FOOD": [
        "hunger", "eat", "feast", "taste", "cook", "flavor", "meal",
        "bread", "drink", "wine", "fruit", "sweet", "bitter", "salt",
        "spice", "harvest", "feed", "nourish", "appetite", "starve",
        "devour", "savor", "grain", "meat", "soup", "roast", "crop",
        "kitchen", "recipe", "ingredient", "banquet", "delicious",
    ],

    "NATURE": [
        "tree", "forest", "river", "mountain", "sky", "cloud", "leaf",
        "stone", "root", "flower", "rain", "wind", "earth", "sun",
        "moon", "star", "ocean", "lake", "grass", "meadow", "valley",
        "cliff", "shore", "stream", "dawn", "dusk", "wilderness",
        "hill", "fog", "snow", "ice", "petal", "bloom", "thorn",
    ],

    "TRAVEL": [
        "journey", "road", "path", "arrive", "depart", "ship", "voyage",
        "wander", "roam", "pilgrim", "destination", "foreign", "horizon",
        "map", "compass", "return", "crossroads", "passage", "distant",
        "abroad", "migrate", "seek", "adventure", "quest", "departure",
        "wanderer", "traveler", "wayfare", "expedition", "caravan",
    ],

    "WAR": [
        "battle", "weapon", "sword", "soldier", "fight", "wound",
        "enemy", "army", "siege", "conquer", "defeat", "blood",
        "cannon", "march", "troop", "commander", "fortress",
        "surrender", "attack", "victory", "warrior", "shield",
        "arrow", "spear", "war", "combat", "campaign", "conflict",
        "slaughter", "captive", "prisoner", "front",
    ],

    "BODY": [
        "heart", "hand", "eye", "face", "breath", "blood", "skin",
        "bone", "muscle", "throat", "shoulder", "chest", "arm",
        "leg", "foot", "head", "ear", "nose", "mouth", "lip",
        "tongue", "finger", "tear", "sweat", "pulse", "vein",
        "wound", "flesh", "forehead", "cheek", "neck", "wrist",
    ],

    "HOME": [
        "house", "room", "door", "window", "family", "shelter",
        "hearth", "nest", "warmth", "comfort", "rest", "kitchen",
        "bed", "roof", "wall", "table", "chair", "welcome", "belong",
        "childhood", "domestic", "threshold", "cottage", "dwelling",
        "haven", "abode", "household", "parent", "garden", "fireplace",
    ],

    "DEATH": [
        "die", "grave", "funeral", "mourn", "ghost", "eternal",
        "decay", "ash", "dust", "burial", "coffin", "corpse",
        "widow", "grief", "loss", "memorial", "cease", "fade",
        "disappear", "shadow", "darkness", "silence", "perish",
        "obituary", "elegy", "requiem", "ruin", "void", "expire",
    ],

    "LOVE": [
        "heart", "kiss", "embrace", "tender", "longing", "cherish",
        "adore", "beloved", "passion", "devotion", "affection",
        "romance", "desire", "faithful", "loyal", "bond", "beauty",
        "sweetness", "gentle", "intimacy", "fond", "rapture",
        "sigh", "yearning", "enchant", "caress", "vow", "oath",
        "attraction", "admire", "infatuation",
    ],

    "POWER": [
        "authority", "command", "rule", "obey", "crown", "throne",
        "dominate", "control", "master", "servant", "king", "queen",
        "govern", "reign", "law", "force", "strength", "will",
        "subjugate", "empire", "conquer", "mighty", "tyrant",
        "noble", "lord", "vassal", "decree", "order", "submission",
    ],

    "RELIGION": [
        "prayer", "sacred", "divine", "soul", "faith", "holy",
        "church", "god", "heaven", "angel", "spirit", "ritual",
        "worship", "miracle", "sin", "grace", "temple", "priest",
        "blessing", "paradise", "eternal", "redemption", "covenant",
        "prophet", "revelation", "scripture", "psalm", "icon",
        "devotion", "salvation", "pilgrimage",
    ],

    "MONEY": [
        "debt", "wealth", "pay", "cost", "trade", "poverty", "coin",
        "gold", "silver", "merchant", "market", "buy", "sell",
        "profit", "loss", "fortune", "beg", "lend", "borrow",
        "price", "rich", "poor", "treasure", "jewel", "afford",
        "bank", "economy", "tax", "wage", "commerce", "luxury",
    ],

    "SCIENCE": [
        "experiment", "theory", "measure", "observe", "discover",
        "hypothesis", "data", "element", "atom", "force", "energy",
        "calculate", "laboratory", "research", "proof", "evidence",
        "test", "analysis", "equation", "method", "logic", "reason",
        "fact", "principle", "mechanism", "gravity", "chemical",
        "biological", "formula", "systematic", "empirical",
    ],

    "TIME": [
        "moment", "memory", "past", "future", "age", "hour", "dawn",
        "dusk", "century", "epoch", "season", "change", "pass",
        "flow", "wait", "brief", "eternal", "once", "then", "remain",
        "youth", "old", "ancient", "instant", "clock", "tide",
        "cycle", "duration", "lapse", "transient", "fleeting",
    ],
}
