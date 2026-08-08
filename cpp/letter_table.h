#pragma once
/**
 * letter_table.h — Numeric value + archetypal category lookup for the
 *                  Somatic/Archetypal Cipher.
 *
 * Exact matrix (per specification):
 *   A=1  (Origin)   | B=2  (Kinetic)   | C=3  (Resonant)  | D=4  (Sovereign)
 *   E=5  (Kinetic)  | F=6  (Kinetic)   | G=7  (Liminal)   | H=8  (Resonant)
 *   I=9  (Sovereign)| J=10 (Kinetic)   | K=11 (Sovereign) | L=12 (Resonant)
 *   M=13 (Resonant) | N=14 (Liminal)   | O=15 (Resonant)  | P=16 (Kinetic)
 *   Q=17 (Sovereign)| R=18 (Liminal)   | S=19 (Kinetic)   | T=20 (Sovereign)
 *   U=21 (Resonant) | V=22 (Kinetic)   | W=23 (Sovereign) | X=24 (Sovereign)
 *   Y=25 (Resonant) | Z=26 (Sovereign)
 *
 * UTF-8 umlauts (2-byte 0xC3 prefix):
 *   Ä=1.5 (Liminal) | Ö=15.5 (Liminal) | Ü=21.5 (Liminal)
 *   (lowercase ä/ö/ü map to the same values)
 *
 * Non-alphabetic characters → value 0.0, category ""
 */

#include <string>

namespace psycho {

struct LetterInfo {
    float       value    = 0.f;
    const char* category = "";  // Static string literal — no allocation
};

/**
 * Look up an uppercase ASCII letter A–Z.
 * Returns {0.f, ""} for any other character.
 */
LetterInfo lookup_ascii(char c);

/**
 * Look up a German umlaut by the second byte of its UTF-8 encoding.
 * The caller must have already confirmed the first byte is 0xC3.
 * Handles both upper- and lower-case variants:
 *   0x84/0xA4 → Ä/ä = 1.5  (Liminal)
 *   0x96/0xB6 → Ö/ö = 15.5 (Liminal)
 *   0x9C/0xBC → Ü/ü = 21.5 (Liminal)
 * Returns {0.f, ""} for any unrecognised second byte.
 */
LetterInfo lookup_umlaut(unsigned char second_byte);

} // namespace psycho
