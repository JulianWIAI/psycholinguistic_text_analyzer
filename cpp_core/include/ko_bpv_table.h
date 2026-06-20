#pragma once
/**
 * ko_bpv_table.h
 * --------------
 * Compile-time lookup tables for the Korean (Hangul) BPV pipeline.
 *
 * 24 bins: 14 basic consonants (0–13) + 10 basic vowels (14–23).
 * Tense consonants (ㄲ ㄸ ㅃ ㅆ ㅉ) fold to their base consonant bin with BPV=9.
 * Compound vowels fold to the primary vowel component's bin.
 * Compound codas fold to the primary consonant's bin.
 *
 * Consonant order: ㄱ(0) ㄴ(1) ㄷ(2) ㄹ(3) ㅁ(4) ㅂ(5) ㅅ(6) ㅇ(7)
 *                  ㅈ(8) ㅊ(9) ㅋ(10) ㅌ(11) ㅍ(12) ㅎ(13)
 * Vowel order:     ㅏ(14) ㅑ(15) ㅓ(16) ㅕ(17) ㅗ(18) ㅛ(19)
 *                  ㅜ(20) ㅠ(21) ㅡ(22) ㅣ(23)
 *
 * Sections:
 *   1. BPV weights (24 bins)
 *   2. Archetypal category enum + lookup table
 *   3. Visual Complexity Anchors
 *   4. Phonosemantic Double-Letter Gm multipliers
 *   5. Interaction Coefficient pairs (7 canonical Korean pairs)
 *   6. Jamo dispatch tables (ONSET[19], NUCLEUS[21], CODA[27])
 *   7. Jamo index mapper (jamo_lookup)
 */

#include <array>
#include <cstdint>
#include <cstddef>

namespace psycho {
namespace ko {

static constexpr int ALPHA_SIZE   = 24;
static constexpr int ONSET_SIZE   = 19;  // U+1100–U+1112
static constexpr int NUCLEUS_SIZE = 21;  // U+1161–U+1175
static constexpr int CODA_SIZE    = 27;  // U+11A8–U+11C2

// ===========================================================================
// 1. Base Psychological Vectors (24 bins)
//
// Phonetic weight rationale:
//   High (8-9): ㅅ(6) ㅊ(9) ㅋ(10) ㅌ(11) ㅍ(12) — aspirated / sibilant, peak tension
//   Mid  (6-7): ㄱ(0) ㄷ(2) ㅂ(5) ㅈ(8) ㄹ(3) ㅎ(13) — plain stops / affricates / liquid
//               ㅏ(14) ㅗ(18) ㅜ(20) ㅣ(23) — open core vowels
//   Low  (3-5): ㄴ(1) ㅁ(4) ㅇ(7) — nasals, neutral placeholder
//               ㅑ(15) ㅕ(17) ㅛ(19) ㅠ(21) ㅡ(22) — glide-compound vowels
// ===========================================================================
//             ㄱ  ㄴ  ㄷ  ㄹ  ㅁ  ㅂ  ㅅ  ㅇ  ㅈ  ㅊ  ㅋ  ㅌ  ㅍ  ㅎ
//             ㅏ  ㅑ  ㅓ  ㅕ  ㅗ  ㅛ  ㅜ  ㅠ  ㅡ  ㅣ
constexpr std::array<uint8_t, ALPHA_SIZE> BPV_KO = {{
    7,  5,  7,  6,  6,  7,  8,  5,  7,  8,  8,  8,  8,  6,
    7,  6,  6,  5,  7,  5,  7,  5,  5,  7
}};

inline constexpr uint8_t bpv_ko(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE)
        return BPV_KO[static_cast<std::size_t>(idx)];
    return 0;
}

// ===========================================================================
// 2. Archetypal categories
//
//   Origin    — ㅏ(14) ㅓ(16) ㅗ(18) ㅜ(20) ㅣ(23)   pure basic vowels
//   Kinetic   — ㄱ(0) ㄷ(2) ㅂ(5) ㅈ(8) ㅊ(9) ㅋ(10) ㅌ(11) ㅍ(12)  stops/affricates
//   Resonant  — ㄴ(1) ㄹ(3) ㅁ(4) ㅅ(6) ㅎ(13)  nasals/liquids/fricatives
//   Liminal   — ㅑ(15) ㅕ(17) ㅛ(19) ㅠ(21) ㅡ(22)  glide-compound vowels
//   Sovereign — ㅇ(7)  null-onset / velar-nasal — ubiquitous placeholder
// ===========================================================================
enum class KoreanArchetype : uint8_t {
    Origin    = 0,
    Kinetic   = 1,
    Resonant  = 2,
    Liminal   = 3,
    Sovereign = 4,
    None      = 5,
};

constexpr std::array<KoreanArchetype, ALPHA_SIZE> KO_ARCHETYPE_TABLE = {{
    KoreanArchetype::Kinetic,    // ㄱ  (0)
    KoreanArchetype::Resonant,   // ㄴ  (1)
    KoreanArchetype::Kinetic,    // ㄷ  (2)
    KoreanArchetype::Resonant,   // ㄹ  (3)
    KoreanArchetype::Resonant,   // ㅁ  (4)
    KoreanArchetype::Kinetic,    // ㅂ  (5)
    KoreanArchetype::Resonant,   // ㅅ  (6)
    KoreanArchetype::Sovereign,  // ㅇ  (7)
    KoreanArchetype::Kinetic,    // ㅈ  (8)
    KoreanArchetype::Kinetic,    // ㅊ  (9)
    KoreanArchetype::Kinetic,    // ㅋ  (10)
    KoreanArchetype::Kinetic,    // ㅌ  (11)
    KoreanArchetype::Kinetic,    // ㅍ  (12)
    KoreanArchetype::Resonant,   // ㅎ  (13)
    KoreanArchetype::Origin,     // ㅏ  (14)
    KoreanArchetype::Liminal,    // ㅑ  (15)
    KoreanArchetype::Origin,     // ㅓ  (16)
    KoreanArchetype::Liminal,    // ㅕ  (17)
    KoreanArchetype::Origin,     // ㅗ  (18)
    KoreanArchetype::Liminal,    // ㅛ  (19)
    KoreanArchetype::Origin,     // ㅜ  (20)
    KoreanArchetype::Liminal,    // ㅠ  (21)
    KoreanArchetype::Liminal,    // ㅡ  (22)
    KoreanArchetype::Origin,     // ㅣ  (23)
}};

inline constexpr KoreanArchetype archetype_ko(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE)
        return KO_ARCHETYPE_TABLE[static_cast<std::size_t>(idx)];
    return KoreanArchetype::None;
}

// ===========================================================================
// 3. Visual Complexity Anchors
// Visually complex Jamo with many strokes: ㄹ(3) ㅊ(9) ㅌ(11) ㅍ(12) ㅎ(13) ㅠ(21)
// ===========================================================================
//     ㄱ     ㄴ     ㄷ     ㄹ     ㅁ     ㅂ     ㅅ     ㅇ     ㅈ     ㅊ     ㅋ
//     ㅌ     ㅍ     ㅎ     ㅏ     ㅑ     ㅓ     ㅕ     ㅗ     ㅛ     ㅜ     ㅠ
//     ㅡ     ㅣ
constexpr bool VISUAL_ANCHOR_KO[ALPHA_SIZE] = {
    false, false, false, true,  false, false, false, false, false, true,  false,
    true,  true,  true,  false, false, false, false, false, false, false, true,
    false, false
};

inline constexpr bool is_visual_anchor_ko(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE) return VISUAL_ANCHOR_KO[idx];
    return false;
}

// ===========================================================================
// 4. Phonosemantic Double-Letter Gm multipliers
//
//   Sibilant               ㅅ(6)                  1.8
//   Affricates             ㅈ(8) ㅊ(9)            1.6
//   Stops (any)            ㄱ(0) ㄷ(2) ㅂ(5) ㅋ(10) ㅌ(11) ㅍ(12)  1.5
//   Nasals / liquid        ㄴ(1) ㄹ(3) ㅁ(4)      1.4
//   Other consonants       ㅇ(7) ㅎ(13)           1.2
//   Vowels                 14–23                   1.3
// ===========================================================================
//         ㄱ    ㄴ    ㄷ    ㄹ    ㅁ    ㅂ    ㅅ    ㅇ    ㅈ    ㅊ    ㅋ
//         ㅌ    ㅍ    ㅎ    ㅏ    ㅑ    ㅓ    ㅕ    ㅗ    ㅛ    ㅜ    ㅠ
//         ㅡ    ㅣ
constexpr double DOUBLE_GM_KO[ALPHA_SIZE] = {
    1.5,  1.4,  1.5,  1.4,  1.4,  1.5,  1.8,  1.2,  1.6,  1.6,  1.5,
    1.5,  1.5,  1.2,  1.3,  1.3,  1.3,  1.3,  1.3,  1.3,  1.3,  1.3,
    1.3,  1.3
};

inline constexpr double double_gm_ko(int idx) noexcept {
    if (idx >= 0 && idx < ALPHA_SIZE) return DOUBLE_GM_KO[idx];
    return 1.0;
}

// ===========================================================================
// 5. Interaction Coefficients — 7 canonical Korean pairs
//
// Keys pack two indices as (min << 8) | max — order-independent lookup.
//   ㄱ+ㄹ  (0+ 3)  Authority Flow       (syntonic,       1.7)
//   ㅅ+ㄴ  (1+ 6)  Suppressed Tension   (dystonic,       0.8)
//   ㄷ+ㅇ  (2+ 7)  Guarded Start        (dystonic,       0.7)
//   ㅁ+ㅏ  (4+14)  Emotional Depth      (syntonic,       1.5)
//   ㄹ+ㅡ  (3+22)  Flowing Restraint    (syntonic,       1.4)
//   ㅈ+ㅣ  (8+23)  Assertive Brightness (syntonic,       1.6)
//   ㅎ+ㄱ  (0+13)  Explosive Emphasis   (transformative, 1.9)
// ===========================================================================

struct KoreanInteractionCoeff {
    double      ic;
    const char* label;
    const char* type;
};

inline constexpr uint16_t ko_ic_key(int a, int b) noexcept {
    const int lo = (a < b) ? a : b;
    const int hi = (a < b) ? b : a;
    return static_cast<uint16_t>(
        (static_cast<uint16_t>(lo) << 8) | static_cast<uint16_t>(hi)
    );
}

struct KoreanInteractionEntry {
    uint16_t              key;
    KoreanInteractionCoeff coeff;
};

constexpr KoreanInteractionEntry KO_INTERACTION_TABLE[7] = {
    { ko_ic_key( 0,  3), { 1.7, "Authority Flow",       "syntonic"       } }, // ㄱ+ㄹ
    { ko_ic_key( 1,  6), { 0.8, "Suppressed Tension",   "dystonic"       } }, // ㅅ+ㄴ
    { ko_ic_key( 2,  7), { 0.7, "Guarded Start",        "dystonic"       } }, // ㄷ+ㅇ
    { ko_ic_key( 4, 14), { 1.5, "Emotional Depth",      "syntonic"       } }, // ㅁ+ㅏ
    { ko_ic_key( 3, 22), { 1.4, "Flowing Restraint",    "syntonic"       } }, // ㄹ+ㅡ
    { ko_ic_key( 8, 23), { 1.6, "Assertive Brightness", "syntonic"       } }, // ㅈ+ㅣ
    { ko_ic_key( 0, 13), { 1.9, "Explosive Emphasis",   "transformative" } }, // ㅎ+ㄱ
};

inline const KoreanInteractionCoeff* find_interaction_ko(int a, int b) noexcept {
    const uint16_t k = ko_ic_key(a, b);
    for (const auto& e : KO_INTERACTION_TABLE)
        if (e.key == k) return &e.coeff;
    return nullptr;
}

// ===========================================================================
// 6. Jamo dispatch tables
//
// Each entry: {bin, bpv} — bin is the 24-bin target; bpv overrides BPV_KO
// for tense consonants and compound forms.
// ===========================================================================

struct JamoBin { int8_t bin; uint8_t bpv; };

// Onset Jamo — U+1100 through U+1112 (19 entries, conjoining choseong)
constexpr JamoBin ONSET_TABLE[ONSET_SIZE] = {
    {  0, 7 }, // U+1100 ㄱ
    {  0, 9 }, // U+1101 ㄲ  tense → ㄱ bin, peak BPV
    {  1, 5 }, // U+1102 ㄴ
    {  2, 7 }, // U+1103 ㄷ
    {  2, 9 }, // U+1104 ㄸ  tense → ㄷ bin
    {  3, 6 }, // U+1105 ㄹ
    {  4, 6 }, // U+1106 ㅁ
    {  5, 7 }, // U+1107 ㅂ
    {  5, 9 }, // U+1108 ㅃ  tense → ㅂ bin
    {  6, 8 }, // U+1109 ㅅ
    {  6, 9 }, // U+110A ㅆ  tense → ㅅ bin
    {  7, 5 }, // U+110B ㅇ  null onset
    {  8, 7 }, // U+110C ㅈ
    {  8, 9 }, // U+110D ㅉ  tense → ㅈ bin
    {  9, 8 }, // U+110E ㅊ
    { 10, 8 }, // U+110F ㅋ
    { 11, 8 }, // U+1110 ㅌ
    { 12, 8 }, // U+1111 ㅍ
    { 13, 6 }, // U+1112 ㅎ
};

// Nucleus Jamo — U+1161 through U+1175 (21 entries, conjoining jungseong)
constexpr JamoBin NUCLEUS_TABLE[NUCLEUS_SIZE] = {
    { 14, 7 }, // U+1161 ㅏ
    { 14, 6 }, // U+1162 ㅐ  ㅏ+ㅣ blend → ㅏ bin
    { 15, 6 }, // U+1163 ㅑ
    { 15, 5 }, // U+1164 ㅒ  ㅑ+ㅣ → ㅑ bin
    { 16, 6 }, // U+1165 ㅓ
    { 16, 5 }, // U+1166 ㅔ  ㅓ+ㅣ → ㅓ bin
    { 17, 5 }, // U+1167 ㅕ
    { 17, 5 }, // U+1168 ㅖ  ㅕ+ㅣ → ㅕ bin
    { 18, 7 }, // U+1169 ㅗ
    { 18, 6 }, // U+116A ㅘ  ㅗ+ㅏ → ㅗ bin
    { 18, 5 }, // U+116B ㅙ  ㅗ+ㅐ → ㅗ bin
    { 18, 6 }, // U+116C ㅚ  ㅗ+ㅣ → ㅗ bin
    { 19, 5 }, // U+116D ㅛ
    { 20, 7 }, // U+116E ㅜ
    { 20, 6 }, // U+116F ㅝ  ㅜ+ㅓ → ㅜ bin
    { 20, 5 }, // U+1170 ㅞ  ㅜ+ㅔ → ㅜ bin
    { 20, 6 }, // U+1171 ㅟ  ㅜ+ㅣ → ㅜ bin
    { 21, 5 }, // U+1172 ㅠ
    { 22, 5 }, // U+1173 ㅡ
    { 22, 5 }, // U+1174 ㅢ  ㅡ+ㅣ → ㅡ bin
    { 23, 7 }, // U+1175 ㅣ
};

// Coda Jamo — U+11A8 through U+11C2 (27 entries, conjoining jongseong)
constexpr JamoBin CODA_TABLE[CODA_SIZE] = {
    {  0, 7 }, // U+11A8 ㄱ
    {  0, 9 }, // U+11A9 ㄲ
    {  6, 7 }, // U+11AA ㄳ  ㄱ+ㅅ compound → ㅅ bin
    {  1, 5 }, // U+11AB ㄴ
    {  1, 5 }, // U+11AC ㄵ  ㄴ+ㅈ → ㄴ bin
    {  1, 5 }, // U+11AD ㄶ  ㄴ+ㅎ → ㄴ bin
    {  2, 7 }, // U+11AE ㄷ
    {  3, 6 }, // U+11AF ㄹ
    {  3, 6 }, // U+11B0 ㄺ  ㄹ+ㄱ → ㄹ bin
    {  3, 6 }, // U+11B1 ㄻ  ㄹ+ㅁ → ㄹ bin
    {  3, 6 }, // U+11B2 ㄼ  ㄹ+ㅂ → ㄹ bin
    {  3, 6 }, // U+11B3 ㄽ  ㄹ+ㅅ → ㄹ bin
    {  3, 6 }, // U+11B4 ㄾ  ㄹ+ㅌ → ㄹ bin
    {  3, 6 }, // U+11B5 ㄿ  ㄹ+ㅍ → ㄹ bin
    {  3, 6 }, // U+11B6 ㅀ  ㄹ+ㅎ → ㄹ bin
    {  4, 6 }, // U+11B7 ㅁ
    {  5, 7 }, // U+11B8 ㅂ
    {  5, 7 }, // U+11B9 ㅄ  ㅂ+ㅅ → ㅂ bin
    {  6, 8 }, // U+11BA ㅅ
    {  6, 9 }, // U+11BB ㅆ  tense
    {  7, 5 }, // U+11BC ㅇ  velar nasal coda
    {  8, 7 }, // U+11BD ㅈ
    {  9, 8 }, // U+11BE ㅊ
    { 10, 8 }, // U+11BF ㅋ
    { 11, 8 }, // U+11C0 ㅌ
    { 12, 8 }, // U+11C1 ㅍ
    { 13, 6 }, // U+11C2 ㅎ
};

// ===========================================================================
// 7. Jamo index mapper
//
// Handles conjoining Jamo (U+1100–U+11FF, from Python decomposition) and
// compatibility Jamo (U+3131–U+3163, standalone form).
// Syllable blocks (U+AC00–U+D7A3) should already be decomposed by Python;
// this function returns {-1,0} for any non-Jamo codepoint.
// ===========================================================================

inline JamoBin jamo_lookup(uint32_t cp) noexcept {
    // Onset conjoining Jamo: U+1100–U+1112
    if (cp >= 0x1100u && cp <= 0x1112u)
        return ONSET_TABLE[static_cast<std::size_t>(cp - 0x1100u)];

    // Nucleus conjoining Jamo: U+1161–U+1175
    if (cp >= 0x1161u && cp <= 0x1175u)
        return NUCLEUS_TABLE[static_cast<std::size_t>(cp - 0x1161u)];

    // Coda conjoining Jamo: U+11A8–U+11C2
    if (cp >= 0x11A8u && cp <= 0x11C2u)
        return CODA_TABLE[static_cast<std::size_t>(cp - 0x11A8u)];

    // Compatibility consonants: U+3131–U+314E (30 entries)
    if (cp >= 0x3131u && cp <= 0x314Eu) {
        static constexpr JamoBin COMPAT_CONS[30] = {
            {  0, 7 }, // 3131 ㄱ
            {  0, 9 }, // 3132 ㄲ
            {  6, 7 }, // 3133 ㄳ → ㅅ bin
            {  1, 5 }, // 3134 ㄴ
            {  1, 5 }, // 3135 ㄵ → ㄴ bin
            {  1, 5 }, // 3136 ㄶ → ㄴ bin
            {  2, 7 }, // 3137 ㄷ
            {  2, 9 }, // 3138 ㄸ
            {  3, 6 }, // 3139 ㄹ
            {  3, 6 }, // 313A ㄺ → ㄹ bin
            {  3, 6 }, // 313B ㄻ → ㄹ bin
            {  3, 6 }, // 313C ㄼ → ㄹ bin
            {  3, 6 }, // 313D ㄽ → ㄹ bin
            {  3, 6 }, // 313E ㄾ → ㄹ bin
            {  3, 6 }, // 313F ㄿ → ㄹ bin
            {  3, 6 }, // 3140 ㅀ → ㄹ bin
            {  4, 6 }, // 3141 ㅁ
            {  5, 7 }, // 3142 ㅂ
            {  5, 9 }, // 3143 ㅃ
            {  5, 7 }, // 3144 ㅄ → ㅂ bin
            {  6, 8 }, // 3145 ㅅ
            {  6, 9 }, // 3146 ㅆ
            {  7, 5 }, // 3147 ㅇ
            {  8, 7 }, // 3148 ㅈ
            {  8, 9 }, // 3149 ㅉ
            {  9, 8 }, // 314A ㅊ
            { 10, 8 }, // 314B ㅋ
            { 11, 8 }, // 314C ㅌ
            { 12, 8 }, // 314D ㅍ
            { 13, 6 }, // 314E ㅎ
        };
        return COMPAT_CONS[static_cast<std::size_t>(cp - 0x3131u)];
    }

    // Compatibility vowels: U+314F–U+3163 (21 entries, same ordering as NUCLEUS_TABLE)
    if (cp >= 0x314Fu && cp <= 0x3163u) {
        const auto off = static_cast<std::size_t>(cp - 0x314Fu);
        if (off < NUCLEUS_SIZE) return NUCLEUS_TABLE[off];
    }

    return { -1, 0 };
}

// ===========================================================================
// UTF-8 string literals for telemetry serialization (index → display glyph)
// ===========================================================================
inline constexpr const char* KO_GLYPH[ALPHA_SIZE] = {
    "ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ",
    "ㅏ","ㅑ","ㅓ","ㅕ","ㅗ","ㅛ","ㅜ","ㅠ","ㅡ","ㅣ"
};

} // namespace ko
} // namespace psycho
