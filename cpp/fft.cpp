/**
 * fft.cpp — Radix-2 Cooley-Tukey FFT implementation.
 *
 * No external dependencies; uses only <complex>, <cmath>, <algorithm>,
 * <stdexcept>, and <vector> from the C++ standard library.
 *
 * Reference: Cooley & Tukey, "An Algorithm for the Machine Calculation of
 * Complex Fourier Series", Mathematics of Computation, 19(90), 1965.
 */

#include "fft.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace psycho {

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

static bool is_power_of_two(std::size_t n) {
    return n > 1 && (n & (n - 1)) == 0;
}

/** Reverse the lowest 'bits' bits of x. */
static std::size_t bit_reverse(std::size_t x, int bits) {
    std::size_t result = 0;
    for (int i = 0; i < bits; ++i) {
        result = (result << 1) | (x & 1u);
        x >>= 1;
    }
    return result;
}

/** Count trailing zeros (= log2 for powers of 2). */
static int log2_exact(std::size_t n) {
    int bits = 0;
    while (n > 1) { n >>= 1; ++bits; }
    return bits;
}

// ---------------------------------------------------------------------------
// Public: in-place FFT
// ---------------------------------------------------------------------------

void fft_inplace(std::vector<std::complex<float>>& data) {
    const std::size_t N = data.size();
    if (N <= 1) return;
    if (!is_power_of_two(N)) {
        throw std::invalid_argument(
            "psycho::fft_inplace — data.size() must be a power of 2");
    }

    // ── Step 1: Bit-reversal permutation ─────────────────────────────────
    const int bits = log2_exact(N);
    for (std::size_t i = 0; i < N; ++i) {
        std::size_t j = bit_reverse(i, bits);
        if (j > i) std::swap(data[i], data[j]);
    }

    // ── Step 2: Cooley-Tukey butterfly stages ────────────────────────────
    constexpr float TWO_PI = 6.28318530717958647f;

    for (std::size_t step = 2; step <= N; step <<= 1) {
        const std::size_t half  = step >> 1;
        const float angle = -TWO_PI / static_cast<float>(step);
        // Twiddle factor for this stage: w_step = e^{i·angle}
        const std::complex<float> w_step(std::cos(angle), std::sin(angle));

        for (std::size_t k = 0; k < N; k += step) {
            std::complex<float> w(1.f, 0.f);
            for (std::size_t j = 0; j < half; ++j) {
                const std::complex<float> t = w * data[k + j + half];
                const std::complex<float> u = data[k + j];
                data[k + j]        = u + t;  // butterfly top
                data[k + j + half] = u - t;  // butterfly bottom
                w *= w_step;                  // advance twiddle
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Public: dominant_harmonics
// ---------------------------------------------------------------------------

std::vector<SpectralPeak> dominant_harmonics(
    const std::vector<float>& signal,
    std::size_t n_fft,
    int         top_k)
{
    // Validate n_fft is power of 2 (caller should ensure this; we enforce it)
    if (!is_power_of_two(n_fft)) {
        throw std::invalid_argument(
            "psycho::dominant_harmonics — n_fft must be a power of 2");
    }

    // ── DC offset removal (mean subtraction) ─────────────────────────────
    // Compute the mean of the real (non-padded) samples ONLY.  Subtracting
    // this mean zeroes the DC component before the FFT so that a large
    // average letter value (≈13 for uniform English text) cannot spill
    // spectral energy into bins 1-5 via the rectangular-window sidelobe
    // structure, which would otherwise artificially inflate those bins and
    // mask genuine steganographic rhythms.
    const std::size_t copy_len = std::min(signal.size(), n_fft);
    float mean = 0.f;
    for (std::size_t i = 0; i < copy_len; ++i) mean += signal[i];
    if (copy_len > 0) mean /= static_cast<float>(copy_len);

    // ── Build padded complex input (mean-centred) ─────────────────────────
    std::vector<std::complex<float>> buf(n_fft, {0.f, 0.f});
    for (std::size_t i = 0; i < copy_len; ++i) {
        buf[i] = { signal[i] - mean, 0.f };
    }
    // Zero-padded tail stays at 0 (already mean-free relative to itself)

    // ── Run FFT ───────────────────────────────────────────────────────────
    fft_inplace(buf);

    // ── Compute magnitudes for positive frequencies (bins 1 .. n_fft/2) ──
    // Bin 0 is the DC component (mean); we skip it as it carries no rhythmic
    // information relevant to steganographic detection.
    const std::size_t half = n_fft / 2;
    struct Candidate { int bin; float mag; };
    std::vector<Candidate> candidates;
    candidates.reserve(half - 1);

    for (std::size_t k = 1; k < half; ++k) {
        candidates.push_back({
            static_cast<int>(k),
            std::abs(buf[k])
        });
    }

    // Sort descending by magnitude
    std::sort(candidates.begin(), candidates.end(),
        [](const Candidate& a, const Candidate& b){ return a.mag > b.mag; });

    // Build output
    const int out_count = std::min(top_k, static_cast<int>(candidates.size()));
    std::vector<SpectralPeak> peaks;
    peaks.reserve(out_count);
    for (int i = 0; i < out_count; ++i) {
        SpectralPeak p;
        p.bin       = candidates[i].bin;
        p.magnitude = candidates[i].mag;
        p.norm_freq = static_cast<float>(candidates[i].bin) / static_cast<float>(n_fft);
        peaks.push_back(p);
    }
    return peaks;
}

} // namespace psycho
