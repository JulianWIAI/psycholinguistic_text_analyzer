/**
 * letter_table.cpp — Implementation of the Somatic/Archetypal Cipher lookup table.
 *
 * Keeping the table in a .cpp file avoids ODR violations when multiple
 * translation units include the header.
 */

#include "letter_table.h"

namespace psycho {

// ---------------------------------------------------------------------------
// ASCII A–Z table  (index 0 = 'A', index 25 = 'Z')
// ---------------------------------------------------------------------------
static constexpr LetterInfo ASCII_TABLE[26] = {
    {  1.0f, "origin"    },  // A
    {  2.0f, "kinetic"   },  // B
    {  3.0f, "resonant"  },  // C
    {  4.0f, "sovereign" },  // D
    {  5.0f, "kinetic"   },  // E
    {  6.0f, "kinetic"   },  // F
    {  7.0f, "liminal"   },  // G
    {  8.0f, "resonant"  },  // H
    {  9.0f, "sovereign" },  // I
    { 10.0f, "kinetic"   },  // J
    { 11.0f, "sovereign" },  // K
    { 12.0f, "resonant"  },  // L
    { 13.0f, "resonant"  },  // M
    { 14.0f, "liminal"   },  // N
    { 15.0f, "resonant"  },  // O
    { 16.0f, "kinetic"   },  // P
    { 17.0f, "sovereign" },  // Q
    { 18.0f, "liminal"   },  // R
    { 19.0f, "kinetic"   },  // S
    { 20.0f, "sovereign" },  // T
    { 21.0f, "resonant"  },  // U
    { 22.0f, "kinetic"   },  // V
    { 23.0f, "sovereign" },  // W
    { 24.0f, "sovereign" },  // X
    { 25.0f, "resonant"  },  // Y
    { 26.0f, "sovereign" },  // Z
};

LetterInfo lookup_ascii(char c) {
    if (c >= 'A' && c <= 'Z') {
        return ASCII_TABLE[static_cast<unsigned char>(c) - 'A'];
    }
    return { 0.f, "" };
}

// ---------------------------------------------------------------------------
// UTF-8 umlaut lookup  (assumes leading byte 0xC3 has already been checked)
// ---------------------------------------------------------------------------
LetterInfo lookup_umlaut(unsigned char second_byte) {
    switch (second_byte) {
        case 0x84: // Ä
        case 0xA4: // ä  (lowercase → same value)
            return {  1.5f, "liminal" };

        case 0x96: // Ö
        case 0xB6: // ö
            return { 15.5f, "liminal" };

        case 0x9C: // Ü
        case 0xBC: // ü
            return { 21.5f, "liminal" };

        default:
            return { 0.f, "" };
    }
}

} // namespace psycho
