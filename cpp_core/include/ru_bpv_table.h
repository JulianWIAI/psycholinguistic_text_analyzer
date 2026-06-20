#pragma once
/**
 * ru_bpv_table.h
 * --------------
 * Compile-time lookup tables for the Cyrillic (Russian) BPV pipeline.
 *
 * Alphabet order follows the standard Russian dictionary sequence (33 letters):
 *   А(0) Б(1) В(2) Г(3) Д(4) Е(5) Ё(6) Ж(7) З(8) И(9) Й(10) К(11) Л(12)
 *   М(13) Н(14) О(15) П(16) Р(17) С(18) Т(19) У(20) Ф(21) Х(22) Ц(23)
 *   Ч(24) Ш(25) Щ(26) Ъ(27) Ы(28) Ь(29) Э(30) Ю(31) Я(32)
 *
 * Ё (U+0401/U+0451) is outside the contiguous U+0410–U+044F block;
 * it is mapped to index 6 via the special-case branch in cyrillic_index().
 *
 * Sections:
 *   1. BPV weights (33 bins)
 *   2. Archetypal category enum + lookup table
 *   3. Visual Complexity Anchors
 *   4. Phonosemantic Double-Letter Gm multipliers
 *   5. Interaction Coefficient pairs (7 canonical Cyrillic pairs)
 *   6. UTF-8 codepoint decoder + Cyrillic index mapper
 */

#include <array>
#include <cstdint>
#include <cstddef>

namespace psycho {
namespace ru {

static constexpr int ALPHA_SIZE = 33;

// ===========================================================================
// 1. Base Psychological Vectors
//
// Phonetic weight rationale:
//   High (8-9): З И — tense/sibilant; А М Ж Ч Щ Ы Я — heavy somatic load
//   Mid  (6-7): Б В Г Д Й К Н О П Р Т Ф Х Ю — standard consonants/vowels
//   Low  (3-5): Е Ё У Ь Э — modifiers, soft vowels, minimal pressure
//               Ъ=3 — hard sign, phonetically inert
// ===========================================================================
//           А   Б   В   Г   Д   Е   Ё   Ж   З   И   Й
//           К   Л   М   Н   О   П   Р   С   Т   У   Ф
//           Х   Ц   Ч   Ш   Щ   Ъ   Ы   Ь   Э   Ю   Я
constexpr std::array<uint8_t, ALPHA_SIZE> BPV_RU = {{
    8,  7,  6,  5,  5,  4,  5,  8,  9,  9,  6,
    8,  6,  8,  7,  5,  7,  7,  6,  7,  5,  6,
    7,  6,  8,  7,  8,  3,  8,  4,  6,  7,  8
}};

/// O(1) BPV lookup by Cyrillic index 0–32; returns 0 for out-of-range.
inline constexpr uint8_t bpv_ru(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE)
        return BPV_RU[static_cast<std::size_t>(idx)];
    return 0;
}

// ===========================================================================
// 2. Archetypal categories
//
// Mapping specified by the Dissonance Engine:
//   Origin    — А О У И Ы     (pure vowels, source resonance)
//   Kinetic   — Б П Д Т Г К Ч Р  (stops, trills, movement energy)
//   Resonant  — В Ж З Л М Н С Х Ш  (fricatives, nasals, liquids)
//   Liminal   — Е Ё Й Ь Ю Я   (modifiers, diphthong-like, transitional)
//   Sovereign — Ф Ц Щ Ъ Э     (structurally heavy, rare, absolute)
// ===========================================================================

enum class CyrillicArchetype : uint8_t {
    Origin    = 0,
    Kinetic   = 1,
    Resonant  = 2,
    Liminal   = 3,
    Sovereign = 4,
    None      = 5,
};

//                  А              Б              В              Г              Д
//                  Е              Ё              Ж              З              И
//                  Й              К              Л              М              Н
//                  О              П              Р              С              Т
//                  У              Ф              Х              Ц              Ч
//                  Ш              Щ              Ъ              Ы              Ь
//                  Э              Ю              Я
constexpr std::array<CyrillicArchetype, ALPHA_SIZE> ARCHETYPE_TABLE = {{
    CyrillicArchetype::Origin,     // А  (0)
    CyrillicArchetype::Kinetic,    // Б  (1)
    CyrillicArchetype::Resonant,   // В  (2)
    CyrillicArchetype::Kinetic,    // Г  (3)
    CyrillicArchetype::Kinetic,    // Д  (4)
    CyrillicArchetype::Liminal,    // Е  (5)
    CyrillicArchetype::Liminal,    // Ё  (6)
    CyrillicArchetype::Resonant,   // Ж  (7)
    CyrillicArchetype::Resonant,   // З  (8)
    CyrillicArchetype::Origin,     // И  (9)
    CyrillicArchetype::Liminal,    // Й  (10)
    CyrillicArchetype::Kinetic,    // К  (11)
    CyrillicArchetype::Resonant,   // Л  (12)
    CyrillicArchetype::Resonant,   // М  (13)
    CyrillicArchetype::Resonant,   // Н  (14)
    CyrillicArchetype::Origin,     // О  (15)
    CyrillicArchetype::Kinetic,    // П  (16)
    CyrillicArchetype::Kinetic,    // Р  (17)
    CyrillicArchetype::Resonant,   // С  (18)
    CyrillicArchetype::Kinetic,    // Т  (19)
    CyrillicArchetype::Origin,     // У  (20)
    CyrillicArchetype::Sovereign,  // Ф  (21)
    CyrillicArchetype::Resonant,   // Х  (22)
    CyrillicArchetype::Sovereign,  // Ц  (23)
    CyrillicArchetype::Kinetic,    // Ч  (24)
    CyrillicArchetype::Resonant,   // Ш  (25)
    CyrillicArchetype::Sovereign,  // Щ  (26)
    CyrillicArchetype::Sovereign,  // Ъ  (27)
    CyrillicArchetype::Origin,     // Ы  (28)
    CyrillicArchetype::Liminal,    // Ь  (29)
    CyrillicArchetype::Sovereign,  // Э  (30)
    CyrillicArchetype::Liminal,    // Ю  (31)
    CyrillicArchetype::Liminal,    // Я  (32)
}};

inline constexpr CyrillicArchetype archetype_ru(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE)
        return ARCHETYPE_TABLE[static_cast<std::size_t>(idx)];
    return CyrillicArchetype::None;
}

// ===========================================================================
// 3. Visual Complexity Anchors — Ж Ш Щ Ы Ю (wide/branching glyphs)
// ===========================================================================
//     А      Б      В      Г      Д      Е      Ё      Ж      З      И      Й
//     К      Л      М      Н      О      П      Р      С      Т      У      Ф
//     Х      Ц      Ч      Ш      Щ      Ъ      Ы      Ь      Э      Ю      Я
constexpr bool VISUAL_ANCHOR_RU[ALPHA_SIZE] = {
    false, false, false, false, false, false, false, true,  false, false, false,
    false, false, false, false, false, false, false, false, false, false, false,
    false, false, false, true,  true,  false, true,  false, false, true,  false
//  Ж=7                                      Ш=25   Щ=26          Ы=28          Ю=31
};

inline constexpr bool is_visual_anchor_ru(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE) return VISUAL_ANCHOR_RU[idx];
    return false;
}

// ===========================================================================
// 4. Phonosemantic Double-Letter Gm multipliers
//
//   Class                  Letters              Gm
//   Sibilants/Fricatives   З С Ш Щ Ж Ф Х       1.8
//   Plosives + Affricates  Б П Д Т Г К Ч Ц     1.6
//   Liquids/Nasals         Л М Н Р               1.4
//   Vowels                 А Е Ё И О У Ы Э Ю Я  1.3
//   Modifiers/Others       В Й Ь Ъ               1.0
// ===========================================================================
//         А    Б    В    Г    Д    Е    Ё    Ж    З    И    Й
//         К    Л    М    Н    О    П    Р    С    Т    У    Ф
//         Х    Ц    Ч    Ш    Щ    Ъ    Ы    Ь    Э    Ю    Я
constexpr double DOUBLE_GM_RU[ALPHA_SIZE] = {
    1.3, 1.6, 1.0, 1.6, 1.6, 1.3, 1.3, 1.8, 1.8, 1.3, 1.0,
    1.6, 1.4, 1.4, 1.4, 1.3, 1.6, 1.4, 1.8, 1.6, 1.3, 1.8,
    1.8, 1.6, 1.6, 1.8, 1.8, 1.0, 1.3, 1.0, 1.3, 1.3, 1.3
};

inline constexpr double double_gm_ru(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE) return DOUBLE_GM_RU[idx];
    return 1.0;
}

// ===========================================================================
// 5. Interaction Coefficients — 7 canonical Cyrillic pairs
//
// Keys pack two indices as (min << 8) | max — order-independent lookup.
// Pairs mirror the Latin system's psychological archetypes:
//   Б+Х  ↔ B+H  Security            (syntonic,       1.5)
//   К+Ш  ↔ K+Z  Aggression          (syntonic,       1.8)
//   Г+О  ↔ C+O  Openness            (syntonic,       1.4)
//   Н+С  ↔ E+S  Suppressed Nerv.    (dystonic,       0.8)
//   В+И  ↔ C+I  Guarded Interaction (dystonic,       0.7)
//   А+С  ↔ A+S  Alertness           (transformative, 1.7)
//   М+Ю  ↔ M+W  Emotional Turmoil   (transformative, 2.0)
//
// Index reference:
//   А=0 Б=1 В=2 Г=3 К=11 М=13 Н=14 О=15 С=18 Х=22 Ш=25 Ю=31
// ===========================================================================

struct CyrillicInteractionCoeff {
    double      ic;
    const char* label;
    const char* type;
};

inline constexpr uint16_t ru_ic_key(int a, int b) noexcept {
    int lo = (a < b) ? a : b;
    int hi = (a < b) ? b : a;
    return static_cast<uint16_t>(
        (static_cast<uint16_t>(lo) << 8) | static_cast<uint16_t>(hi)
    );
}

struct CyrillicInteractionEntry {
    uint16_t                 key;
    CyrillicInteractionCoeff coeff;
};

constexpr CyrillicInteractionEntry RU_INTERACTION_TABLE[7] = {
    { ru_ic_key( 1, 22), { 1.5, "Security",               "syntonic"       } }, // Б+Х
    { ru_ic_key(11, 25), { 1.8, "Aggression",             "syntonic"       } }, // К+Ш
    { ru_ic_key( 3, 15), { 1.4, "Openness",               "syntonic"       } }, // Г+О
    { ru_ic_key(14, 18), { 0.8, "Suppressed Nervousness", "dystonic"       } }, // Н+С
    { ru_ic_key( 2,  9), { 0.7, "Guarded Interaction",    "dystonic"       } }, // В+И
    { ru_ic_key( 0, 18), { 1.7, "Alertness",              "transformative" } }, // А+С
    { ru_ic_key(13, 31), { 2.0, "Emotional Turmoil",      "transformative" } }, // М+Ю
};

inline const CyrillicInteractionCoeff* find_interaction_ru(int a, int b) noexcept {
    const uint16_t k = ru_ic_key(a, b);
    for (const auto& e : RU_INTERACTION_TABLE)
        if (e.key == k) return &e.coeff;
    return nullptr;
}

// ===========================================================================
// 6. UTF-8 codepoint decoder + Cyrillic index mapper
//
// Cyrillic Unicode layout (uppercase):
//   Ё = U+0401  (isolated; not in the А–Я block)
//   А–Е = U+0410–U+0415  → indices 0–5
//   Ж–Я = U+0416–U+042F  → indices 7–32  (Ё at 6 breaks the run)
//
// Lowercase mirrors uppercase +0x20, except ё = U+0451.
// Both are normalized to the same index as their uppercase counterpart.
// ===========================================================================

/// Decode one UTF-8 codepoint starting at s[i], advance i past it.
/// Returns 0 and advances i by 1 for any invalid or overlong sequence.
inline uint32_t utf8_next(
    const unsigned char* s,
    std::size_t          n,
    std::size_t&         i
) noexcept {
    if (i >= n) return 0;
    const unsigned char b0 = s[i];

    // 1-byte (ASCII)
    if (b0 < 0x80) { ++i; return b0; }

    // 2-byte: 110xxxxx 10xxxxxx  — covers entire Cyrillic block U+0400–U+04FF
    if ((b0 & 0xE0u) == 0xC0u && i + 1 < n) {
        const unsigned char b1 = s[i + 1];
        if ((b1 & 0xC0u) == 0x80u) {
            i += 2;
            return (static_cast<uint32_t>(b0 & 0x1Fu) << 6) | (b1 & 0x3Fu);
        }
    }

    // 3-byte: 1110xxxx 10xxxxxx 10xxxxxx
    if ((b0 & 0xF0u) == 0xE0u && i + 2 < n) {
        const unsigned char b1 = s[i + 1], b2 = s[i + 2];
        if ((b1 & 0xC0u) == 0x80u && (b2 & 0xC0u) == 0x80u) {
            i += 3;
            return (static_cast<uint32_t>(b0 & 0x0Fu) << 12)
                 | (static_cast<uint32_t>(b1 & 0x3Fu) <<  6)
                 | (b2 & 0x3Fu);
        }
    }

    // 4-byte (emoji / SMP): skip entirely — not Cyrillic
    if ((b0 & 0xF8u) == 0xF0u && i + 3 < n) { i += 4; return 0; }

    ++i; return 0; // invalid byte — skip
}

/// Map a Unicode codepoint to Cyrillic alphabet index 0–32.
/// Returns -1 if the codepoint is not a recognized Cyrillic letter.
inline constexpr int cyrillic_index(uint32_t cp) noexcept {
    // Ё / ё — special case outside the contiguous block
    if (cp == 0x0401u || cp == 0x0451u) return 6;

    // Uppercase А–Е (0x0410–0x0415) → 0–5
    if (cp >= 0x0410u && cp <= 0x0415u) return static_cast<int>(cp - 0x0410u);

    // Uppercase Ж–Я (0x0416–0x042F) → 7–32  (+1 offset for Ё at index 6)
    if (cp >= 0x0416u && cp <= 0x042Fu) return static_cast<int>(cp - 0x0410u + 1u);

    // Lowercase а–е (0x0430–0x0435) → 0–5
    if (cp >= 0x0430u && cp <= 0x0435u) return static_cast<int>(cp - 0x0430u);

    // Lowercase ж–я (0x0436–0x044Fu) → 7–32
    if (cp >= 0x0436u && cp <= 0x044Fu) return static_cast<int>(cp - 0x0430u + 1u);

    return -1; // not a Cyrillic alpha codepoint
}

/// True when cp decodes to a valid Cyrillic letter index.
inline constexpr bool is_cyrillic_alpha(uint32_t cp) noexcept {
    return cyrillic_index(cp) >= 0;
}

// UTF-8 string literals for telemetry serialization (index → display glyph)
inline constexpr const char* RU_GLYPH[ALPHA_SIZE] = {
    "А","Б","В","Г","Д","Е","Ё","Ж","З","И","Й",
    "К","Л","М","Н","О","П","Р","С","Т","У","Ф",
    "Х","Ц","Ч","Ш","Щ","Ъ","Ы","Ь","Э","Ю","Я"
};

} // namespace ru
} // namespace psycho
