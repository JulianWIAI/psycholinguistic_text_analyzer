#pragma once
/**
 * bpv_table.h
 * -----------
 * Compile-time lookup tables for the entire orthographic pipeline.
 * Every constant here is a direct port of the Python source values.
 * All arrays are constexpr — the compiler resolves every lookup at compile
 * time and generates a single load instruction at the call site.
 *
 * Sections:
 *   1. Base Psychological Vectors (BPV)
 *   2. Positional multipliers
 *   3. Visual Complexity Anchors
 *   4. Phonosemantic Double-Letter Multipliers (Gm)
 *   5. Interaction Coefficients (7 canonical pairs)
 */

#include <array>
#include <cstdint>
#include <cstring>   // std::strlen

namespace psycho {

// ===========================================================================
// 1. Base Psychological Vectors  A=0 … Z=25
//    Source: orthographic_analyzer.py BPV dict
// ===========================================================================
//               A   B   C   D   E   F   G   H   I   J   K   L   M
//               N   O   P   Q   R   S   T   U   V   W   X   Y   Z
constexpr std::array<uint8_t, 26> BPV_TABLE = {{
    8,  7,  5,  6,  4,  6,  5,  7,  9,  4,  8,  6,  8,
    7,  5,  7,  6,  7,  6,  7,  5,  6,  8,  7,  5,  9
}};

/// O(1) BPV lookup; returns 0 for any non-uppercase-ASCII byte.
inline constexpr uint8_t bpv(unsigned char c) noexcept {
    if (c >= 'A' && c <= 'Z') return BPV_TABLE[c - 'A'];
    return 0;
}

// ===========================================================================
// 2. Positional multipliers
//    Source: _POS_START / _POS_MIDDLE / _POS_END in orthographic_analyzer.py
// ===========================================================================
inline constexpr double POS_START  = 1.50;
inline constexpr double POS_MIDDLE = 1.00;
inline constexpr double POS_END    = 0.75;

// ===========================================================================
// 3. Visual Complexity Anchors  — W, M, K trigger word-level ×1.2
//    Source: _VISUAL_COMPLEXITY frozenset in orthographic_analyzer.py
// ===========================================================================
//                A  B  C  D  E  F  G  H  I  J   K  L  M
//                N  O  P  Q  R  S  T  U  V  W   X  Y  Z
constexpr bool VISUAL_ANCHOR_TABLE[26] = {
    false, false, false, false, false, false, false, false, false, false,
    true,  false, true,  false, false, false, false, false, false, false,
    false, false, true,  false, false, false
//  K=10               M=12                             W=22
};

/// Returns true if *c* (uppercase ASCII) is a visual complexity anchor.
inline constexpr bool is_visual_anchor(unsigned char c) noexcept {
    if (c >= 'A' && c <= 'Z') return VISUAL_ANCHOR_TABLE[c - 'A'];
    return false;
}

// ===========================================================================
// 4. Phonosemantic Double-Letter Multipliers (Gm)
//    Source: _DEFAULT_DOUBLE_GM dict in orthographic_analyzer.py
//
//    Class           Letters      Gm
//    Sibilants/Fric  S F V Z     1.8
//    Plosives        B D P T K G C  1.6
//    Liquids/Nasals  L M N R     1.4
//    Vowels          A E I O U   1.3
//    All others                  1.0
// ===========================================================================
//                   A     B     C     D     E     F     G     H     I     J
//                   K     L     M     N     O     P     Q     R     S     T
//                   U     V     W     X     Y     Z
constexpr double DOUBLE_GM_TABLE[26] = {
    1.3,  1.6,  1.6,  1.6,  1.3,  1.8,  1.6,  1.0,  1.3,  1.0,
    1.6,  1.4,  1.4,  1.4,  1.3,  1.6,  1.0,  1.4,  1.8,  1.6,
    1.3,  1.8,  1.0,  1.0,  1.0,  1.8
};

/// Returns the Gm multiplier for an exact double-letter (uppercase ASCII).
inline constexpr double double_gm(unsigned char c) noexcept {
    if (c >= 'A' && c <= 'Z') return DOUBLE_GM_TABLE[c - 'A'];
    return 1.0;
}

// ===========================================================================
// 5. Interaction Coefficients — 7 canonical letter-pair overrides
//    Source: _RAW_PAIRS list in orthographic_analyzer.py
//
//    Canonical key: pack two uppercase chars as (min_char << 8) | max_char
//    so the lookup is always order-independent.
//
//    Pair   I_c   Label                  Type
//    B,H    1.5   Security               syntonic
//    K,Z    1.8   Aggression             syntonic
//    C,O    1.4   Openness               syntonic
//    E,S    0.8   Suppressed Nervousness dystonic
//    C,I    0.7   Guarded Interaction    dystonic
//    A,S    1.7   Alertness              transformative
//    M,W    2.0   Emotional Turmoil      transformative
// ===========================================================================

struct InteractionCoeff {
    double      ic;
    const char* label;
    const char* type;
};

/// Pack two uppercase chars into a canonical uint16_t key.
/// min char in high byte, max char in low byte — order-independent.
inline constexpr uint16_t ic_key(char a, char b) noexcept {
    // Put the alphabetically smaller character in the high byte.
    unsigned char lo = (a < b) ? static_cast<unsigned char>(a)
                                : static_cast<unsigned char>(b);
    unsigned char hi = (a < b) ? static_cast<unsigned char>(b)
                                : static_cast<unsigned char>(a);
    return static_cast<uint16_t>((lo << 8) | hi);
}

struct InteractionEntry {
    uint16_t       key;
    InteractionCoeff coeff;
};

/// The 7 canonical pairs — linear scan is optimal for N=7.
constexpr InteractionEntry INTERACTION_TABLE[7] = {
    { ic_key('B','H'), { 1.5, "Security",               "syntonic"       } },
    { ic_key('K','Z'), { 1.8, "Aggression",             "syntonic"       } },
    { ic_key('C','O'), { 1.4, "Openness",               "syntonic"       } },
    { ic_key('E','S'), { 0.8, "Suppressed Nervousness", "dystonic"       } },
    { ic_key('C','I'), { 0.7, "Guarded Interaction",    "dystonic"       } },
    { ic_key('A','S'), { 1.7, "Alertness",              "transformative" } },
    { ic_key('M','W'), { 2.0, "Emotional Turmoil",      "transformative" } },
};

/// Returns the matching InteractionCoeff or nullptr if the pair is not found.
inline const InteractionCoeff* find_interaction(
    unsigned char a, unsigned char b
) noexcept {
    uint16_t k = ic_key(static_cast<char>(a), static_cast<char>(b));
    for (const auto& entry : INTERACTION_TABLE) {
        if (entry.key == k) return &entry.coeff;
    }
    return nullptr;
}

} // namespace psycho
