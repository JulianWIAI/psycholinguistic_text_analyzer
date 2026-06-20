#pragma once
/**
 * ar_bpv_table.h
 * --------------
 * Compile-time lookup tables for the Arabic (AR, 28-bin) and Farsi (FA, 32-bin)
 * Abjad BPV pipelines.
 *
 * Index order follows the abjadi (dictionary) sequence — the 28 canonical Arabic
 * consonants, with 4 Farsi-specific letters appended for FA mode:
 *
 * AR indices 0–27 (abjadi order):
 *   ا(0) ب(1) ت(2) ث(3) ج(4) ح(5) خ(6) د(7) ذ(8) ر(9) ز(10) س(11)
 *   ش(12) ص(13) ض(14) ط(15) ظ(16) ع(17) غ(18) ف(19) ق(20) ك(21) ل(22)
 *   م(23) ن(24) ه(25) و(26) ي(27)
 *
 * FA extension indices 28–31:
 *   پ(28) چ(29) ژ(30) گ(31)
 *
 * Sections:
 *   1. BPV weights (28-bin AR / 32-bin FA)
 *   2. Archetypal category enum + lookup tables
 *   3. Visual Complexity Anchors (emphatic & pharyngeal forms)
 *   4. Phonosemantic Double-Letter Gm multipliers
 *   5. Interaction Coefficient pairs (7 canonical Abjad pairs)
 *   6. UTF-8 codepoint decoder + Abjad index mapper
 *
 * Critical design note — LOGICAL ORDER:
 *   The index mapper operates on the UTF-8 byte stream in the exact order
 *   keystrokes were typed (logical order). No reversal is performed for RTL
 *   rendering.  The FFT and Burstiness engines see the logical keystroke
 *   sequence, which is the forensically meaningful signal.
 */

#include <array>
#include <cstdint>
#include <cstddef>

namespace psycho {
namespace ar {

static constexpr int ALPHA_SIZE_AR = 28;
static constexpr int ALPHA_SIZE_FA = 32;

// ===========================================================================
// 1. Base Psychological Vectors
//
// Phonosemantic weight rationale (Abjad model):
//   High (8–9): ض ع — uniquely Arabic emphatics; maximum somatic load
//               ص ط ح — emphatic/pharyngeal; structural weight
//               ج ر ق غ — affricate, trill, uvular stop/fricative
//   Mid  (6–7): ب ت خ د ز ش ف ك ل م ن — standard consonants
//   Low  (4–5): ا ث ذ ه و ي — vowel carrier, glottal, semivowels
//
// Arabic 28-bin (abjadi order):
//        ا   ب   ت   ث   ج   ح   خ   د   ذ   ر   ز   س   ش   ص   ض   ط   ظ   ع   غ   ف   ق   ك   ل   م   ن   ه   و   ي
constexpr std::array<uint8_t, ALPHA_SIZE_AR> BPV_AR = {{
    5,  7,  6,  5,  8,  8,  7,  6,  5,  8,  7,  6,  7,  8,  9,  8,  7,  9,  8,  6,  8,  7,  6,  7,  6,  4,  5,  5
}};

// Farsi 32-bin: same 28 AR weights plus پ(7) چ(7) ژ(7) گ(6)
constexpr std::array<uint8_t, ALPHA_SIZE_FA> BPV_FA = {{
    5,  7,  6,  5,  8,  8,  7,  6,  5,  8,  7,  6,  7,  8,  9,  8,  7,  9,  8,  6,  8,  7,  6,  7,  6,  4,  5,  5,
    7,  7,  7,  6
}};

inline constexpr uint8_t bpv_ar(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE_AR)
        return BPV_AR[static_cast<std::size_t>(idx)];
    return 0;
}

inline constexpr uint8_t bpv_fa(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE_FA)
        return BPV_FA[static_cast<std::size_t>(idx)];
    return 0;
}

// ===========================================================================
// 2. Archetypal categories
//
// Mapping mirrors the Cyrillic five-category system:
//   Origin    — ا و ي         (vowel carrier, semivowels — source resonance)
//   Kinetic   — ب ت ج د ر ق ك ط ض (stops, trills, affricates — movement energy)
//   Resonant  — ث ز س ش ف ل م ن غ  (fricatives, nasals, liquids)
//   Liminal   — ذ ه           (dental fricative, glottal — transitional)
//   Sovereign — ح خ ص ظ ع    (pharyngeal/emphatic — rare, structurally absolute)
//
// Farsi extras: پ(Kinetic) چ(Kinetic) ژ(Resonant) گ(Kinetic)
// ===========================================================================

enum class AbjadArchetype : uint8_t {
    Origin    = 0,
    Kinetic   = 1,
    Resonant  = 2,
    Liminal   = 3,
    Sovereign = 4,
    None      = 5,
};

//                      ا               ب               ت               ث               ج               ح               خ
//                      د               ذ               ر               ز               س               ش               ص
//                      ض               ط               ظ               ع               غ               ف               ق
//                      ك               ل               م               ن               ه               و               ي
constexpr std::array<AbjadArchetype, ALPHA_SIZE_AR> ARCHETYPE_TABLE_AR = {{
    AbjadArchetype::Origin,     // ا (0)
    AbjadArchetype::Kinetic,    // ب (1)
    AbjadArchetype::Kinetic,    // ت (2)
    AbjadArchetype::Resonant,   // ث (3)
    AbjadArchetype::Kinetic,    // ج (4)
    AbjadArchetype::Sovereign,  // ح (5)
    AbjadArchetype::Sovereign,  // خ (6)
    AbjadArchetype::Kinetic,    // د (7)
    AbjadArchetype::Liminal,    // ذ (8)
    AbjadArchetype::Kinetic,    // ر (9)
    AbjadArchetype::Resonant,   // ز (10)
    AbjadArchetype::Resonant,   // س (11)
    AbjadArchetype::Resonant,   // ش (12)
    AbjadArchetype::Sovereign,  // ص (13)
    AbjadArchetype::Kinetic,    // ض (14)
    AbjadArchetype::Kinetic,    // ط (15)
    AbjadArchetype::Sovereign,  // ظ (16)
    AbjadArchetype::Sovereign,  // ع (17)
    AbjadArchetype::Resonant,   // غ (18)
    AbjadArchetype::Resonant,   // ف (19)
    AbjadArchetype::Kinetic,    // ق (20)
    AbjadArchetype::Kinetic,    // ك (21)
    AbjadArchetype::Resonant,   // ل (22)
    AbjadArchetype::Resonant,   // م (23)
    AbjadArchetype::Resonant,   // ن (24)
    AbjadArchetype::Liminal,    // ه (25)
    AbjadArchetype::Origin,     // و (26)
    AbjadArchetype::Origin,     // ي (27)
}};

// FA extension archetypes (indices 28–31)
constexpr std::array<AbjadArchetype, 4> ARCHETYPE_TABLE_FA_EXT = {{
    AbjadArchetype::Kinetic,    // پ (28)
    AbjadArchetype::Kinetic,    // چ (29)
    AbjadArchetype::Resonant,   // ژ (30)
    AbjadArchetype::Kinetic,    // گ (31)
}};

inline constexpr AbjadArchetype archetype_ar(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE_AR)
        return ARCHETYPE_TABLE_AR[static_cast<std::size_t>(idx)];
    if (idx >= ALPHA_SIZE_AR && idx < ALPHA_SIZE_FA)
        return ARCHETYPE_TABLE_FA_EXT[static_cast<std::size_t>(idx - ALPHA_SIZE_AR)];
    return AbjadArchetype::None;
}

// ===========================================================================
// 3. Visual Complexity Anchors
//
// Emphatic & pharyngeal letters carry the highest visual load in Arabic script:
//   ش(12) — three-dot post-alveolar;  ص(13) ض(14) ط(15) ظ(16) — emphatic forms
//   ع(17) ع(17) غ(18) — pharyngeal loop forms
// ===========================================================================
//         ا      ب      ت      ث      ج      ح      خ      د      ذ      ر      ز      س      ش      ص      ض      ط      ظ      ع      غ      ف      ق      ك      ل      م      ن      ه      و      ي
constexpr bool VISUAL_ANCHOR_AR[ALPHA_SIZE_AR] = {
    false, false, false, false, false, false, false, false, false, false, false, false, true,  true,  true,  true,  true,  true,  true,  false, false, false, false, false, false, false, false, false
//  ا      ب      ت      ث      ج      ح      خ      د      ذ      ر      ز      س      ش=12  ص=13  ض=14  ط=15  ظ=16  ع=17  غ=18  ف      ق      ك      ل      م      ن      ه      و      ي
};

// Farsi extension: none of the 4 extra letters carry additional visual complexity
constexpr bool VISUAL_ANCHOR_FA_EXT[4] = { false, false, false, false };

inline constexpr bool is_visual_anchor_ar(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE_AR) return VISUAL_ANCHOR_AR[idx];
    if (idx >= ALPHA_SIZE_AR && idx < ALPHA_SIZE_FA)
        return VISUAL_ANCHOR_FA_EXT[idx - ALPHA_SIZE_AR];
    return false;
}

// ===========================================================================
// 4. Phonosemantic Double-Letter Gm multipliers
//
//   Class                           Letters              Gm
//   Pharyngeal / Emphatic           ح خ ص ض ط ظ ع غ ق   1.8
//   Sibilants                       ز س ش                1.6
//   Stops / Affricates / Trill      ب ت ج د ر ك پ چ گ   1.5
//   Liquids / Nasals                ل م ن ر              1.4
//   Vowels / Semivowels             ا و ي                1.3
//   Fricatives / Transitionals      ث ذ ف ه ژ            1.0
// ===========================================================================
//         ا    ب    ت    ث    ج    ح    خ    د    ذ    ر    ز    س    ش    ص    ض    ط    ظ    ع    غ    ف    ق    ك    ل    م    ن    ه    و    ي
constexpr double DOUBLE_GM_AR[ALPHA_SIZE_AR] = {
    1.3, 1.5, 1.5, 1.0, 1.5, 1.8, 1.8, 1.5, 1.0, 1.5, 1.6, 1.6, 1.6, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.0, 1.8, 1.5, 1.4, 1.4, 1.4, 1.0, 1.3, 1.3
};

// FA extension Gm:  پ=1.5  چ=1.5  ژ=1.6  گ=1.5
constexpr double DOUBLE_GM_FA_EXT[4] = { 1.5, 1.5, 1.6, 1.5 };

inline constexpr double double_gm_ar(int idx, bool is_farsi = false) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE_AR) return DOUBLE_GM_AR[idx];
    if (is_farsi && idx >= ALPHA_SIZE_AR && idx < ALPHA_SIZE_FA)
        return DOUBLE_GM_FA_EXT[idx - ALPHA_SIZE_AR];
    return 1.0;
}

// ===========================================================================
// 5. Interaction Coefficients — 7 canonical Abjad pairs
//
// Keys pack two indices as (min << 8) | max — order-independent lookup.
// Pairs are selected for their forensic-linguistic discriminatory value:
//
//   ع(17)+ر(9)   Authority / Power       (syntonic,       1.8) — pharyngeal+trill
//   ص(13)+ب(1)   Precision Strike        (syntonic,       1.7) — emphatic+bilabial
//   ا(0) +م(23)  Compassion / Origin     (syntonic,       1.5) — vowel+nasal
//   ن(24)+س(11)  Suppressed Nervousness  (dystonic,       0.8) — nasal+sibilant
//   خ(6) +ق(20)  Concealed Threat        (dystonic,       0.7) — velar+uvular
//   ذ(8) +ه(25)  Ephemeral / Fleeting    (transformative, 1.6) — light fricatives
//   ج(4) +ع(17)  Confrontation           (transformative, 2.0) — affricate+pharyngeal
// ===========================================================================

struct AbjadInteractionCoeff {
    double      ic;
    const char* label;
    const char* type;
};

inline constexpr uint16_t ar_ic_key(int a, int b) noexcept {
    int lo = (a < b) ? a : b;
    int hi = (a < b) ? b : a;
    return static_cast<uint16_t>(
        (static_cast<uint16_t>(lo) << 8) | static_cast<uint16_t>(hi)
    );
}

struct AbjadInteractionEntry {
    uint16_t              key;
    AbjadInteractionCoeff coeff;
};

constexpr AbjadInteractionEntry AR_INTERACTION_TABLE[7] = {
    { ar_ic_key( 9, 17), { 1.8, "Authority Power",          "syntonic"       } }, // ع+ر
    { ar_ic_key( 1, 13), { 1.7, "Precision Strike",         "syntonic"       } }, // ص+ب
    { ar_ic_key( 0, 23), { 1.5, "Compassion",               "syntonic"       } }, // ا+م
    { ar_ic_key(11, 24), { 0.8, "Suppressed Nervousness",   "dystonic"       } }, // ن+س
    { ar_ic_key( 6, 20), { 0.7, "Concealed Threat",         "dystonic"       } }, // خ+ق
    { ar_ic_key( 8, 25), { 1.6, "Ephemeral",                "transformative" } }, // ذ+ه
    { ar_ic_key( 4, 17), { 2.0, "Confrontation",            "transformative" } }, // ج+ع
};

inline const AbjadInteractionCoeff* find_interaction_ar(int a, int b) noexcept {
    const uint16_t k = ar_ic_key(a, b);
    for (const auto& e : AR_INTERACTION_TABLE)
        if (e.key == k) return &e.coeff;
    return nullptr;
}

// ===========================================================================
// 6. UTF-8 codepoint decoder + Abjad index mapper
//
// Arabic Unicode layout (U+0600–U+06FF block):
//   All Arabic letters are encoded in 2-byte UTF-8 sequences.
//   Primary Arabic consonants cluster in U+0621–U+064A with three gaps:
//     U+0629 (ة Ta Marbuta) — word-final marker, not a primary consonant → skip
//     U+063B–U+0640 — non-letter code points → skip
//     U+0649 (ى Alef Maqsura) — maps to ي index 27
//   Alef variant forms (U+0622, U+0623, U+0625) all map to index 0.
//   Farsi-specific letters: U+067E پ, U+0686 چ, U+0698 ژ, U+06AF گ.
//
// The utf8_next() function is shared with the Cyrillic engine (defined in
// ru_bpv_table.h, namespace psycho::ru). It handles 2-byte sequences
// covering the entire U+0080–U+07FF range including U+0600–U+06FF.
//
// CRITICAL — Logical vs. Visual Order:
//   arabic_index() is called on the byte stream in the order it was received
//   (logical/keyboarding order).  RTL visual rendering is a UI concern only.
//   The BPV engine, FFT, and Burstiness calculations all operate on the
//   logical sequence to preserve forensic fidelity of inter-keystroke timing.
// ===========================================================================

/// Sparse dispatch table: offset from U+0627.
/// Size = 0x064A − 0x0627 + 1 = 36 entries.
static constexpr int8_t AR_CODEPOINT_TABLE[36] = {
//  ا   ب  ة   ت   ث   ج   ح   خ   د   ذ
    0,  1, -1,  2,  3,  4,  5,  6,  7,  8,
//  ر   ز   س   ش   ص   ض   ط   ظ   ع   غ
    9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
//  U+063B..U+063F (unused)         U+0640 Tatweel
   -1, -1, -1, -1, -1,            -1,
//  ف   ق   ك   ل   م   ن   ه   و   ى  ي
   19, 20, 21, 22, 23, 24, 25, 26, 27, 27
};

/// Map a Unicode codepoint to Abjad alphabet index.
/// @param cp       Unicode codepoint to map.
/// @param is_farsi True when the FA 32-bin engine is active (enables پچژگ).
/// @returns Alphabet index 0–27 (AR) or 0–31 (FA), or -1 if not a letter.
inline constexpr int arabic_index(uint32_t cp, bool is_farsi) noexcept {
    // Farsi-specific letters — checked first to avoid table-range confusion
    if (is_farsi) {
        if (cp == 0x067Eu) return 28; // پ Pe
        if (cp == 0x0686u) return 29; // چ Che
        if (cp == 0x0698u) return 30; // ژ Zhe
        if (cp == 0x06AFu) return 31; // گ Gaf
    }

    // Alef variant forms all resolve to index 0
    if (cp == 0x0622u || cp == 0x0623u || cp == 0x0625u) return 0; // آ أ إ
    // Waw with Hamza → Waw
    if (cp == 0x0624u) return 26; // ؤ
    // Ya with Hamza → Ya
    if (cp == 0x0626u) return 27; // ئ

    // Primary Arabic consonant block U+0627–U+064A
    if (cp < 0x0627u || cp > 0x064Au) return -1;
    return AR_CODEPOINT_TABLE[static_cast<std::size_t>(cp - 0x0627u)];
}

inline constexpr bool is_arabic_alpha(uint32_t cp, bool is_farsi) noexcept {
    return arabic_index(cp, is_farsi) >= 0;
}

// UTF-8 glyph strings for telemetry serialization (index → display glyph)
// AR 28-letter set
inline constexpr const char* AR_GLYPH[ALPHA_SIZE_AR] = {
    "ا","ب","ت","ث","ج","ح","خ","د","ذ","ر","ز","س","ش","ص","ض","ط","ظ","ع","غ","ف","ق","ك","ل","م","ن","ه","و","ي"
};

// FA 32-letter set (28 Arabic + 4 Farsi)
inline constexpr const char* FA_GLYPH[ALPHA_SIZE_FA] = {
    "ا","ب","ت","ث","ج","ح","خ","د","ذ","ر","ز","س","ش","ص","ض","ط","ظ","ع","غ","ف","ق","ك","ل","م","ن","ه","و","ي",
    "پ","چ","ژ","گ"
};

} // namespace ar
} // namespace psycho
