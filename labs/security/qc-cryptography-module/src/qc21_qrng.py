"""
QC-21: QRNG (Quantum Random Number Generator)
True randomness from quantum vacuum fluctuations + NIST SP 800-22 tests.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import hashlib
import struct
import numpy as np


# ---------------------------------------------------------------------------
# QRNG source models
# ---------------------------------------------------------------------------

def photon_path_superposition(n_bits: int = 10000, seed: int = None) -> np.ndarray:
    """
    Model: photon in |+⟩ = (|0⟩+|1⟩)/√2 measured in {|0⟩,|1⟩} basis.
    Each bit is maximally random: P(0) = P(1) = 0.5.
    Simulation uses numpy default_rng for quantum randomness model.
    """
    rng = np.random.default_rng(seed)  # would be hardware quantum source in reality
    return rng.integers(0, 2, size=n_bits, dtype=np.int32)


def photon_arrival_time(n_bits: int = 10000, seed: int = None) -> np.ndarray:
    """
    Model: photon arrival time quantized; LSB of arrival time quantum-random.
    Exponential inter-arrival times → random binary bits via LSB extraction.
    """
    rng = np.random.default_rng(seed)
    arrival_times = rng.exponential(scale=1.0, size=n_bits)
    # Extract LSB of microsecond timestamp
    bits = (np.floor(arrival_times * 1e6).astype(np.int64) & 1).astype(np.int32)
    return bits


def vacuum_fluctuations(n_bits: int = 10000, seed: int = None) -> np.ndarray:
    """
    Model: vacuum field quadrature measurement → Gaussian noise → thresholded.
    ⟨X̂⟩ = 0, ⟨X̂²⟩ = 1/2 (vacuum shot noise).
    """
    rng = np.random.default_rng(seed)
    quadrature = rng.standard_normal(size=n_bits)  # vacuum fluctuations
    return (quadrature > 0).astype(np.int32)


def prng_aes_ctr_drbg(n_bits: int = 10000, seed_bytes: bytes = b"deterministic_seed") -> np.ndarray:
    """
    Classical AES-CTR-DRBG pseudorandom generator (deterministic).
    Passes NIST tests but is deterministic — not truly random.
    """
    bits = []
    counter = 0
    while len(bits) < n_bits:
        block = hashlib.sha256(seed_bytes + counter.to_bytes(8, "little")).digest()
        for byte in block:
            for bit in range(8):
                bits.append((byte >> bit) & 1)
                if len(bits) >= n_bits:
                    break
            if len(bits) >= n_bits:
                break
        counter += 1
    return np.array(bits[:n_bits], dtype=np.int32)


# ---------------------------------------------------------------------------
# Min-entropy (NIST SP 800-90B)
# ---------------------------------------------------------------------------

def min_entropy(bits: np.ndarray) -> float:
    """
    H_min = -log2(p_max) where p_max is the max probability of any single symbol.
    For binary bits: p_max = max(P(0), P(1)).
    Full SP 800-90B uses a more complex estimator; this is the iid approximation.
    """
    n = len(bits)
    p1 = float(np.sum(bits)) / n
    p0 = 1.0 - p1
    p_max = max(p0, p1)
    if p_max >= 1.0:
        return 0.0
    return -math.log2(p_max)


# ---------------------------------------------------------------------------
# NIST SP 800-22 randomness tests (simplified)
# ---------------------------------------------------------------------------

def nist_frequency_test(bits: np.ndarray) -> dict:
    """
    Frequency (monobit) test: Z = S_n / √n where S_n = sum(±1).
    H0: P(0) = P(1) = 0.5.
    """
    n = len(bits)
    s_n = int(2 * np.sum(bits) - n)   # +1 for 1, -1 for 0
    z = abs(s_n) / math.sqrt(n)
    import math as _math
    # p-value via complementary error function: p = erfc(|Z|/√2)
    p_value = math.erfc(z / math.sqrt(2))
    return {
        "test": "Frequency (Monobit)",
        "S_n": s_n,
        "Z_score": round(z, 4),
        "p_value": round(p_value, 4),
        "pass": p_value >= 0.01,
    }


def nist_block_frequency_test(bits: np.ndarray, block_size: int = 128) -> dict:
    """
    Block frequency test: chi-squared statistic over blocks.
    """
    n = len(bits)
    n_blocks = n // block_size
    if n_blocks == 0:
        return {"test": "Block Frequency", "pass": False, "note": "Too few bits"}
    chi_sq = 0.0
    for i in range(n_blocks):
        block = bits[i * block_size:(i + 1) * block_size]
        pi_i = float(np.sum(block)) / block_size
        chi_sq += 4 * block_size * (pi_i - 0.5) ** 2
    # p-value: chi-sq with n_blocks DOF — approximate via normal
    # Use Wilson-Hilferty approximation for chi-sq CDF
    k = n_blocks
    if k > 0:
        x = chi_sq
        # Approximate p-value: p = 1 - F_chi2(x, k)
        # Use Gaussian approx: z = (x - k) / sqrt(2k)
        z = (x - k) / math.sqrt(2 * k)
        p_value = 0.5 * math.erfc(z / math.sqrt(2))
    else:
        p_value = 0.0
    return {
        "test": "Block Frequency",
        "n_blocks": n_blocks,
        "chi_squared": round(chi_sq, 4),
        "p_value": round(p_value, 4),
        "pass": p_value >= 0.01,
    }


def nist_runs_test(bits: np.ndarray) -> dict:
    """
    Runs test: count runs (consecutive same bits), compare to expected.
    """
    n = len(bits)
    pi = float(np.sum(bits)) / n
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return {
            "test": "Runs",
            "pi": round(pi, 4),
            "pass": False,
            "note": "Pre-condition failed (pi too far from 0.5)",
        }
    # Count runs
    v_n = 1 + int(np.sum(bits[:-1] != bits[1:]))  # number of runs
    expected = 2 * n * pi * (1 - pi)
    stddev = 2 * math.sqrt(n) * pi * (1 - pi)
    z = abs(v_n - expected) / stddev if stddev > 0 else 0.0
    p_value = math.erfc(z / math.sqrt(2))
    return {
        "test": "Runs",
        "v_n": v_n,
        "expected_runs": round(expected, 2),
        "Z_score": round(z, 4),
        "p_value": round(p_value, 4),
        "pass": p_value >= 0.01,
    }


def nist_spectral_test(bits: np.ndarray) -> dict:
    """
    DFT (spectral) test: detect periodic patterns.
    """
    n = len(bits)
    s = (2 * bits.astype(np.float64)) - 1   # ±1 encoding
    fft_vals = np.fft.rfft(s)
    magnitudes = np.abs(fft_vals[1:n // 2])
    threshold = math.sqrt(math.log(1.0 / 0.05) * n)  # 95th percentile threshold
    n_peaks_below = int(np.sum(magnitudes < threshold))
    expected_below = int(0.95 * (n // 2 - 1))
    d = (n_peaks_below - expected_below) / math.sqrt(n * 0.95 * 0.05 / 4)
    p_value = math.erfc(abs(d) / math.sqrt(2))
    return {
        "test": "Spectral (DFT)",
        "peaks_below_threshold": n_peaks_below,
        "expected_below": expected_below,
        "d_statistic": round(d, 4),
        "p_value": round(p_value, 4),
        "pass": p_value >= 0.01,
    }


def run_nist_suite(bits: np.ndarray, source_name: str) -> dict:
    """Run all 4 NIST tests and return summary."""
    freq = nist_frequency_test(bits)
    block = nist_block_frequency_test(bits)
    runs = nist_runs_test(bits)
    spectral = nist_spectral_test(bits)
    tests = [freq, block, runs, spectral]
    all_pass = all(t.get("pass", False) for t in tests)
    return {
        "source": source_name,
        "min_entropy": round(min_entropy(bits), 6),
        "tests": tests,
        "all_pass": all_pass,
        "bits_tested": len(bits),
    }


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()
    n = 10000
    seed = 42

    sources = {
        "QRNG-Photon-Path": photon_path_superposition(n, seed=seed),
        "QRNG-Arrival-Time": photon_arrival_time(n, seed=seed),
        "QRNG-Vacuum-Fluct": vacuum_fluctuations(n, seed=seed),
        "PRNG-AES-CTR-DRBG": prng_aes_ctr_drbg(n),
    }

    nist_results = {}
    for name, bits in sources.items():
        nist_results[name] = run_nist_suite(bits, name)

    result = {
        "scenario": "QC-21",
        "name": "QRNG — Quantum Random Number Generator",
        "category": "Primitive",
        "n_bits_per_source": n,
        "nist_results": nist_results,
        "use_cases": [
            "Cryptographic key generation (AES-256, ML-KEM)",
            "Quantum nonce generation (prevents replay attacks)",
            "Quantum lottery and gambling (certified randomness)",
            "Cryptographic seeding (provably unbiased seeds)",
        ],
        "prng_vs_qrng": (
            "PRNG (AES-CTR-DRBG): passes all NIST tests but is deterministic. "
            "Given seed, adversary can predict all output. "
            "QRNG: each bit comes from quantum measurement collapse — fundamentally unpredictable "
            "even to an adversary with unlimited computation. "
            "QRNG proves non-determinism by the laws of quantum mechanics (Born rule)."
        ),
        "min_entropy_threshold": 0.95,
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    res = run_scenario()
    print("=" * 60)
    print(f"QC-21: {res['name']}")
    print("=" * 60)
    print()
    for name, nr in res["nist_results"].items():
        status = "✓ ALL PASS" if nr["all_pass"] else "✗ SOME FAIL"
        print(f"Source: {name}")
        print(f"  Min-entropy H_min = {nr['min_entropy']:.6f}  "
              f"{'≥0.95 ✓' if nr['min_entropy'] >= 0.95 else '<0.95 ✗'}")
        for t in nr["tests"]:
            p_str = f"{t.get('p_value', 'N/A')}"
            pass_str = "PASS" if t.get("pass") else "FAIL"
            print(f"  [{pass_str}] {t['test']:<30} p={p_str}")
        print(f"  Overall: {status}")
        print()
    print(f"PRNG vs QRNG: {res['prng_vs_qrng']}")
    print()
    print("Use cases:", ", ".join(res["use_cases"]))
    print(f"Elapsed: {res['elapsed_s']}s")
