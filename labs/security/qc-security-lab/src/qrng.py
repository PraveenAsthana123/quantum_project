#!/usr/bin/env python3
"""
QC-21: QRNG (Quantum Random Number Generator) Simulation.

Reference papers:
  - Jennewein et al., "A fast and compact QRNG", arXiv:quant-ph/9912118
  - Ma et al., "Quantum random number generation", npj Quantum Information (2016)
  - NIST SP 800-90B (2018) — Recommendation for entropy sources

Simulates:
  1. Photon arrival time (Poisson process) — the physical entropy source
  2. Min-entropy estimation per NIST SP 800-90B
  3. NIST SP 800-22 randomness test suite (subset): Frequency, Block Frequency, Runs, DFT
  4. LFSR (Linear Feedback Shift Register) PRNG for comparison
  5. Comparative entropy quality: QRNG vs PRNG
"""

import os
import math
import time
import random
import struct
import hashlib
from typing import List, Tuple, Dict


# ---------------------------------------------------------------------------
# 1. Photon Arrival Time Simulation (Poisson process)
# ---------------------------------------------------------------------------

class PhotonQRNG:
    """
    Simulates photon arrival times from a single-photon source.
    Generates random bits via:
      - Time-bin detection: photon in early (0) or late (1) window
      - Or: inter-arrival time parity (odd/even in units of Δt)
    """

    def __init__(self, photon_rate: float = 1e6, time_resolution_ns: float = 0.1):
        """
        photon_rate: mean photon arrivals per second
        time_resolution_ns: detector time resolution in nanoseconds
        """
        self.rate = photon_rate
        self.dt_ns = time_resolution_ns
        self.mean_interval_ns = 1e9 / photon_rate  # ns

    def generate_arrival_times(self, n_photons: int) -> List[float]:
        """
        Sample inter-arrival times from exponential distribution (Poisson process).
        Returns list of arrival times in nanoseconds.
        """
        times = []
        t = 0.0
        for _ in range(n_photons):
            # Exponential inter-arrival time
            dt = -self.mean_interval_ns * math.log(max(random.random(), 1e-15))
            t += dt
            times.append(t)
        return times

    def time_bin_bits(self, n_bits: int, window_ns: float = None) -> List[int]:
        """
        Generate bits using time-bin detection.
        Each photon is in 'early' (0) or 'late' (1) half of the detection window.
        """
        if window_ns is None:
            window_ns = self.mean_interval_ns

        arrivals = self.generate_arrival_times(n_bits * 2)  # oversample
        bits = []
        for t in arrivals:
            # Position within current window
            pos = t % window_ns
            bit = 0 if pos < window_ns / 2 else 1
            bits.append(bit)
            if len(bits) >= n_bits:
                break
        return bits[:n_bits]

    def inter_arrival_parity_bits(self, n_bits: int) -> List[int]:
        """
        Generate bits from parity of inter-arrival time bins.
        More entropy than time-bin (uses continuous randomness).
        """
        arrivals = self.generate_arrival_times(n_bits + 10)
        intervals = [arrivals[i + 1] - arrivals[i] for i in range(len(arrivals) - 1)]
        bits = []
        for interval in intervals:
            bins = int(interval / self.dt_ns)
            bits.append(bins % 2)
            if len(bits) >= n_bits:
                break
        return bits[:n_bits]


# ---------------------------------------------------------------------------
# 2. LFSR PRNG for comparison
# ---------------------------------------------------------------------------

class LFSR_PRNG:
    """
    Linear Feedback Shift Register (maximal-length LFSR).
    Deterministic — poor entropy, predictable given state knowledge.
    """
    TAPS_16 = [16, 15, 13, 4]  # maximal-length polynomial for 16-bit LFSR

    def __init__(self, seed: int = None, bits: int = 16):
        if seed is None:
            seed = int.from_bytes(os.urandom(2), "big") or 1
        self.state = seed & ((1 << bits) - 1)
        self.bits = bits
        self.taps = self.TAPS_16

    def next_bit(self) -> int:
        feedback = 0
        for tap in self.taps:
            feedback ^= (self.state >> (self.bits - tap)) & 1
        self.state = ((self.state << 1) | feedback) & ((1 << self.bits) - 1)
        return (self.state >> (self.bits - 1)) & 1

    def generate_bits(self, n: int) -> List[int]:
        return [self.next_bit() for _ in range(n)]


# ---------------------------------------------------------------------------
# 3. Min-entropy estimation (NIST SP 800-90B § 6.3)
# ---------------------------------------------------------------------------

def min_entropy_most_common_value(bits: List[int]) -> float:
    """
    MCV (Most Common Value) estimator — NIST SP 800-90B Section 6.3.1.
    Hmin = -log2(p_max)
    """
    n = len(bits)
    if n == 0:
        return 0.0
    counts = {0: bits.count(0), 1: bits.count(1)}
    p_max = max(counts.values()) / n
    return -math.log2(p_max) if p_max > 0 else 1.0


def min_entropy_markov(bits: List[int]) -> float:
    """
    Markov estimator — accounts for sequential dependencies.
    NIST SP 800-90B Section 6.3.3 (simplified).
    """
    if len(bits) < 4:
        return 1.0
    # Estimate P(b_i | b_{i-1})
    trans = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
    counts = {0: 0, 1: 0}
    for i in range(len(bits) - 1):
        trans[(bits[i], bits[i + 1])] += 1
        counts[bits[i]] += 1
    # P(next | prev) — find max
    p_max = 0.0
    for prev in [0, 1]:
        if counts[prev] == 0:
            continue
        for nxt in [0, 1]:
            p = trans[(prev, nxt)] / counts[prev]
            p_max = max(p_max, p)
    return -math.log2(p_max) if p_max > 0 else 1.0


def collision_entropy(bits: List[int]) -> float:
    """
    Renyi collision entropy H2 = -log2(sum p_i^2).
    """
    n = len(bits)
    p0 = bits.count(0) / n
    p1 = 1 - p0
    h2 = -math.log2(p0 ** 2 + p1 ** 2) if (p0 > 0 or p1 > 0) else 1.0
    return h2


# ---------------------------------------------------------------------------
# 4. NIST SP 800-22 Randomness Tests (subset)
# ---------------------------------------------------------------------------

def test_frequency(bits: List[int]) -> Tuple[bool, float]:
    """
    NIST Test 1: Monobit Frequency Test.
    Tests whether proportion of 1s ≈ 0.5.
    """
    n = len(bits)
    s = sum(2 * b - 1 for b in bits)  # ±1
    s_obs = abs(s) / math.sqrt(n)
    # p-value via erfc
    p_val = math.erfc(s_obs / math.sqrt(2))
    return p_val >= 0.01, p_val


def test_block_frequency(bits: List[int], block_size: int = 128) -> Tuple[bool, float]:
    """
    NIST Test 2: Block Frequency Test.
    For each block, proportion of 1s should be ≈ 0.5.
    """
    n = len(bits)
    m = block_size
    n_blocks = n // m
    if n_blocks == 0:
        return True, 1.0

    chi_sq = 0.0
    for i in range(n_blocks):
        block = bits[i * m:(i + 1) * m]
        pi = sum(block) / m
        chi_sq += (pi - 0.5) ** 2

    chi_sq *= 4 * m
    # Approximate p-value using chi-squared CDF
    k = n_blocks
    # Use regularized incomplete gamma function approximation
    p_val = _igamc(k / 2, chi_sq / 2)
    return p_val >= 0.01, p_val


def test_runs(bits: List[int]) -> Tuple[bool, float]:
    """
    NIST Test 3: Runs Test.
    Checks number of runs (consecutive identical bits).
    """
    n = len(bits)
    pi = sum(bits) / n
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return False, 0.0

    v_obs = sum(1 for i in range(n - 1) if bits[i] != bits[i + 1]) + 1
    p_num = abs(v_obs - 2 * n * pi * (1 - pi))
    p_den = 2 * math.sqrt(2 * n) * pi * (1 - pi)
    if p_den < 1e-10:
        return True, 1.0
    p_val = math.erfc(p_num / p_den)
    return p_val >= 0.01, p_val


def test_dft(bits: List[int]) -> Tuple[bool, float]:
    """
    NIST Test 6: Discrete Fourier Transform (Spectral) Test.
    Checks for periodicity.
    """
    n = len(bits)
    x = [2 * b - 1 for b in bits]  # ±1

    # Simple DFT (magnitude of first n/2 components)
    magnitudes = []
    for k in range(1, n // 2 + 1):
        re = sum(x[j] * math.cos(2 * math.pi * k * j / n) for j in range(n))
        im = sum(x[j] * math.sin(2 * math.pi * k * j / n) for j in range(n))
        magnitudes.append(math.sqrt(re ** 2 + im ** 2))

    threshold = math.sqrt(math.log(1.0 / 0.05) * n)
    n_below = sum(1 for m in magnitudes if m < threshold)
    n0 = 0.95 * n / 2
    n_above_mean = (n // 2 - n_below) - n // 2 * 0.05
    d = (n_above_mean - 0) / math.sqrt(n * 0.95 * 0.05 / 4) if n > 0 else 0
    p_val = math.erfc(abs(d) / math.sqrt(2))
    return p_val >= 0.01, p_val


def _igamc(a: float, x: float) -> float:
    """Approximation of regularized upper incomplete gamma function."""
    if x < 0:
        return 1.0
    if x == 0:
        return 1.0
    # Simple approximation using series
    try:
        # Use chi-squared survival function approximation
        # P(chi2 > x) with k=2a degrees of freedom
        k = 2 * a
        # Normal approximation for large k
        z = ((x / k) ** (1 / 3) - (1 - 2 / (9 * k))) / math.sqrt(2 / (9 * k))
        return 0.5 * math.erfc(z / math.sqrt(2))
    except (ValueError, ZeroDivisionError):
        return 0.5


def run_nist_tests(bits: List[int]) -> Dict[str, dict]:
    results = {}

    pass_freq, p_freq = test_frequency(bits)
    results["frequency"] = {"pass": pass_freq, "p_value": round(p_freq, 6)}

    pass_bf, p_bf = test_block_frequency(bits)
    results["block_frequency"] = {"pass": pass_bf, "p_value": round(p_bf, 6)}

    pass_runs, p_runs = test_runs(bits)
    results["runs"] = {"pass": pass_runs, "p_value": round(p_runs, 6)}

    # DFT is slow for large n; cap at 1000 bits
    if len(bits) >= 100:
        pass_dft, p_dft = test_dft(bits[:min(1000, len(bits))])
        results["dft"] = {"pass": pass_dft, "p_value": round(p_dft, 6)}
    else:
        results["dft"] = {"pass": None, "p_value": None, "note": "Need ≥100 bits"}

    return results


# ---------------------------------------------------------------------------
# 5. Main comparison: QRNG vs PRNG
# ---------------------------------------------------------------------------

def main():
    N_BITS = 10_000
    print("=" * 65)
    print("QRNG vs PRNG Entropy Quality Comparison")
    print(f"Reference: NIST SP 800-90B | Ma et al. npj QI (2016)")
    print(f"Sample size: {N_BITS} bits")
    print("=" * 65)

    qrng = PhotonQRNG(photon_rate=1e6, time_resolution_ns=0.1)
    prng = LFSR_PRNG()
    os_rng_bits = [int(b) for byte in os.urandom(N_BITS // 8) for b in f"{byte:08b}"]

    print("\nGenerating QRNG bits (photon time-bin)...")
    t0 = time.perf_counter()
    qrng_bits = qrng.time_bin_bits(N_BITS)
    qrng_time = (time.perf_counter() - t0) * 1000

    print("Generating LFSR PRNG bits...")
    t0 = time.perf_counter()
    prng_bits = prng.generate_bits(N_BITS)
    prng_time = (time.perf_counter() - t0) * 1000

    datasets = [
        ("QRNG (time-bin)", qrng_bits),
        ("LFSR PRNG", prng_bits),
        ("OS urandom", os_rng_bits),
    ]

    print("\n--- Min-Entropy Estimates (NIST SP 800-90B) ---")
    print(f"{'Source':<22} {'MCV Hmin':>10} {'Markov Hmin':>12} {'H2 (Renyi)':>12}")
    print("-" * 58)
    for name, bits in datasets:
        h_mcv = min_entropy_most_common_value(bits)
        h_markov = min_entropy_markov(bits)
        h2 = collision_entropy(bits)
        print(f"{name:<22} {h_mcv:>10.4f} {h_markov:>12.4f} {h2:>12.4f}")

    print("\n--- NIST SP 800-22 Randomness Tests ---")
    print(f"{'Source':<22} {'Frequency':>12} {'Block Freq':>12} {'Runs':>12} {'DFT':>12}")
    print("-" * 72)
    for name, bits in datasets:
        nist = run_nist_tests(bits)
        def fmt(r):
            if r["pass"] is None:
                return "N/A"
            return f"{'PASS' if r['pass'] else 'FAIL'} p={r['p_value']:.3f}"
        print(f"{name:<22} {fmt(nist['frequency']):>18} {fmt(nist['block_frequency']):>18} "
              f"{fmt(nist['runs']):>12} {fmt(nist['dft']):>12}")

    print("\n--- Generation Speed ---")
    print(f"  QRNG (simulated photon)  : {qrng_time:.1f} ms for {N_BITS} bits")
    print(f"  LFSR PRNG                : {prng_time:.1f} ms for {N_BITS} bits")

    print("\n--- Physical QRNG Performance (real devices) ---")
    print(f"{'Device':<30} {'Rate':>12} {'Entropy/bit':>14} {'Principle':>20}")
    print("-" * 80)
    physical = [
        ("ID Quantique QRNG chip",   "1 Gbit/s",  "≥0.999",   "Vacuum fluctuation"),
        ("PicoQuant τ-SPAD",         "100 Mbit/s","≥0.998",   "Photon arrival time"),
        ("NIST SP 800-90A AES-CTR",  "N/A (PRNG)","<1.0",     "Deterministic PRNG"),
        ("LFSR (16-bit)",            "fast",       "~0.5",     "Linear recurrence"),
        ("Intel RDRAND",             "~800 Mbit/s","≥0.999",  "Thermal noise + CSPRNG"),
    ]
    for row in physical:
        print(f"{row[0]:<30} {row[1]:>12} {row[2]:>14} {row[3]:>20}")

    print("\nConclusion:")
    print("  QRNG sources entropy from fundamental quantum randomness.")
    print("  LFSR PRNG is completely deterministic given the seed — 0 entropy.")
    print("  OS urandom = CSPRNG seeded with OS entropy (hardware events).")
    print("  For cryptographic keys: OS urandom ≈ QRNG in practice;")
    print("  QRNG avoids any seed-compromise risk at the hardware level.")


if __name__ == "__main__":
    main()
