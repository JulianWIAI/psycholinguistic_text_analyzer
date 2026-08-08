#pragma once
/**
 * fft.h — Dependency-free Radix-2 Cooley-Tukey FFT (standard library only).
 *
 * Public API:
 *   fft_inplace()      — in-place FFT on a power-of-2 complex vector
 *   dominant_harmonics()— convenience: run FFT on a real signal and return
 *                         the top-k spectral peaks (excluding DC bin 0)
 */

#include "types.h"        // SpectralPeak
#include <vector>
#include <complex>
#include <cstddef>

namespace psycho {

/**
 * In-place Radix-2 Cooley-Tukey FFT.
 *
 * @param data  Complex input/output vector.  data.size() MUST be a power of 2.
 * @throws std::invalid_argument if size is not a power of 2.
 *
 * After the call, data[k] holds the complex frequency-domain coefficient X[k].
 */
void fft_inplace(std::vector<std::complex<float>>& data);

/**
 * Compute the top-k dominant spectral peaks of a real-valued signal.
 *
 * Algorithm:
 *   1. Pad/truncate the signal to exactly n_fft samples (must be power of 2).
 *   2. Run FFT.
 *   3. Compute |X[k]| for k = 1 .. n_fft/2  (skip DC bin 0).
 *   4. Return the top_k bins sorted by descending magnitude.
 *
 * @param signal  Real-valued input (letter values).
 * @param n_fft   FFT size — must be a power of 2 (default: 256).
 * @param top_k   Number of peaks to return (default: 5).
 */
std::vector<SpectralPeak> dominant_harmonics(
    const std::vector<float>& signal,
    std::size_t n_fft = 256,
    int         top_k = 5
);

} // namespace psycho
