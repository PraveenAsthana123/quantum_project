"""
CUSTOMER DEMO PITCH — Quantum Random Number Generator (QRNG)
=============================================================
True random numbers are the foundation of cryptographic key material.
Classical PRNGs (Mersenne Twister, /dev/urandom) are deterministic from their seed —
given the seed and algorithm, EVERY future bit is predictable.

A QRNG generates bits from quantum measurement outcomes, which are provably
non-deterministic — not just computationally unpredictable.

This demo:
  1. Generates 256 bits by measuring qubits prepared in |+⟩ superposition.
  2. Runs NIST SP 800-90B-inspired statistical tests on the quantum bit string.
  3. Compares to Python's PRNG (seeded) showing determinism.
  4. Estimates entropy per bit.

Audience: Security engineers, cryptographers, compliance officers.
Runtime: < 10 seconds.
"""

import math
import struct
import random as stdlib_random
import numpy as np

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 66
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


# ---------------------------------------------------------------------------
# QRNG: generate bits via quantum measurement
# ---------------------------------------------------------------------------

def qrng_bits(n_bits: int) -> list:
    """
    Generate n_bits random bits by measuring H|0⟩ qubits.
    Batch into 8-qubit circuits to keep circuits small.
    """
    sim = AerSimulator()
    bits = []
    batch = 8
    while len(bits) < n_bits:
        qc = QuantumCircuit(batch)
        qc.h(range(batch))
        qc.measure_all()
        result = sim.run(qc, shots=1).result()
        counts = result.get_counts()
        bitstring = list(counts.keys())[0]
        bits.extend([int(b) for b in bitstring])
    return bits[:n_bits]


def prng_bits(n_bits: int, seed: int) -> list:
    """Generate n_bits from Python's Mersenne Twister PRNG with fixed seed."""
    rng = stdlib_random.Random(seed)
    return [rng.randint(0, 1) for _ in range(n_bits)]


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def frequency_test(bits: list) -> dict:
    """
    NIST SP 800-22 Frequency (Monobit) Test.
    Tests if the number of 1s equals the number of 0s.
    Passes if |p_ones - 0.5| < threshold.
    """
    n      = len(bits)
    ones   = sum(bits)
    p_ones = ones / n
    s      = abs(ones - n / 2) / math.sqrt(n / 4)   # test statistic (z-score)
    # p-value (two-sided)
    from math import erfc
    p_val  = erfc(s / math.sqrt(2))
    return {"ones": ones, "zeros": n - ones, "p_ones": p_ones,
            "statistic": s, "p_value": p_val, "pass": p_val > 0.01}


def runs_test(bits: list) -> dict:
    """
    NIST Runs Test: counts total number of runs (consecutive same-value sequences).
    A 'run' is a consecutive series of identical bits.
    For a random sequence, expected runs ≈ n/2.
    """
    n    = len(bits)
    runs = 1
    for i in range(1, n):
        if bits[i] != bits[i - 1]:
            runs += 1
    p_ones = sum(bits) / n
    # Exact mean and variance under H0
    mu_runs  = 2 * n * p_ones * (1 - p_ones) + 1
    var_runs = 2 * n * p_ones * (1 - p_ones) * (2 * n * p_ones * (1 - p_ones) - 1) \
               / ((n - 1) if n > 1 else 1)
    var_runs = max(var_runs, 1e-10)
    z        = abs(runs - mu_runs) / math.sqrt(var_runs)
    from math import erfc
    p_val    = erfc(z / math.sqrt(2))
    return {"runs": runs, "expected_runs": mu_runs, "z_score": z,
            "p_value": p_val, "pass": p_val > 0.01}


def chi_squared_test(bits: list, block_size: int = 8) -> dict:
    """
    Chi-squared uniformity test on byte values.
    Group bits into bytes, test if all 256 byte values are roughly equally likely.
    Only valid for large n.
    """
    n = len(bits)
    n_bytes = n // block_size
    if n_bytes == 0:
        return {"skip": True}

    counts = [0] * 256
    for i in range(n_bytes):
        byte = 0
        for j in range(block_size):
            byte = (byte << 1) | bits[i * block_size + j]
        counts[byte] += 1

    expected = n_bytes / 256
    chi2 = sum((c - expected) ** 2 / expected for c in counts if expected > 0)
    dof  = 255   # 256 categories - 1
    # P-value from chi-squared CDF (approximation using normal for large dof)
    z    = (chi2 - dof) / math.sqrt(2 * dof)
    from math import erfc
    p_val = 0.5 * erfc(z / math.sqrt(2))
    return {"chi2": chi2, "dof": dof, "p_value": p_val, "pass": p_val > 0.01,
            "n_bytes": n_bytes, "expected_per_bin": expected}


def entropy_estimate(bits: list) -> float:
    """
    Min-entropy estimate from bit frequencies.
    H_min = -log2(max probability) — conservative NIST SP 800-90B metric.
    """
    n    = len(bits)
    ones = sum(bits)
    p_max = max(ones / n, (n - ones) / n)
    return -math.log2(p_max)


# ---------------------------------------------------------------------------
# Determinism demonstration
# ---------------------------------------------------------------------------

def prng_determinism_demo(n_bits: int = 32, seed: int = 12345) -> None:
    b1 = prng_bits(n_bits, seed)
    b2 = prng_bits(n_bits, seed)
    print(f"  PRNG seed={seed}, run 1: {''.join(str(b) for b in b1)}")
    print(f"  PRNG seed={seed}, run 2: {''.join(str(b) for b in b2)}")
    identical = b1 == b2
    print(f"  Identical: {identical}  ← PRNG is DETERMINISTIC from seed")


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    N_BITS = 256

    print_sep("QUANTUM RANDOM NUMBER GENERATOR (QRNG) DEMO")
    print(f"  Generating {N_BITS} quantum random bits via H|0⟩ measurement...\n")

    # Generate quantum bits
    q_bits = qrng_bits(N_BITS)
    q_str  = ''.join(str(b) for b in q_bits)
    print_sep("Generated Quantum Bit String (256 bits)")
    for i in range(0, N_BITS, 64):
        print(f"  {q_str[i:i+64]}")
    print()

    # Generate PRNG bits for comparison
    p_bits = prng_bits(N_BITS, seed=42)
    p_str  = ''.join(str(b) for b in p_bits)
    print(f"  PRNG (seed=42) bits:")
    for i in range(0, N_BITS, 64):
        print(f"  {p_str[i:i+64]}")
    print()

    # Statistical tests — quantum
    print_sep("NIST SP 800-90B Statistical Tests — Quantum Bits")
    fq = frequency_test(q_bits)
    rq = runs_test(q_bits)
    cq = chi_squared_test(q_bits)
    Hq = entropy_estimate(q_bits)

    print(f"  Frequency (Monobit) Test:")
    print(f"    Ones: {fq['ones']}/{N_BITS}  ({fq['p_ones']*100:.1f}%)  "
          f"Statistic: {fq['statistic']:.4f}  p-value: {fq['p_value']:.4f}  "
          f"{'PASS ✓' if fq['pass'] else 'FAIL ✗'}")
    print(f"  Runs Test:")
    print(f"    Runs: {rq['runs']}  Expected: {rq['expected_runs']:.1f}  "
          f"Z: {rq['z_score']:.4f}  p-value: {rq['p_value']:.4f}  "
          f"{'PASS ✓' if rq['pass'] else 'FAIL ✗'}")
    if not cq.get("skip"):
        print(f"  Chi-Squared Uniformity Test (bytes):")
        print(f"    χ²={cq['chi2']:.2f}  df={cq['dof']}  "
              f"p-value={cq['p_value']:.4f}  "
              f"{'PASS ✓' if cq['pass'] else 'FAIL ✗'}")
    print(f"  Min-Entropy estimate: {Hq:.4f} bits/bit  (ideal = 1.000)")
    print()

    # Statistical tests — PRNG
    print_sep("NIST SP 800-90B Statistical Tests — PRNG Bits (seed=42)")
    fp = frequency_test(p_bits)
    rp = runs_test(p_bits)
    cp = chi_squared_test(p_bits)
    Hp = entropy_estimate(p_bits)

    print(f"  Frequency (Monobit) Test:")
    print(f"    Ones: {fp['ones']}/{N_BITS}  ({fp['p_ones']*100:.1f}%)  "
          f"Statistic: {fp['statistic']:.4f}  p-value: {fp['p_value']:.4f}  "
          f"{'PASS ✓' if fp['pass'] else 'FAIL ✗'}")
    print(f"  Runs Test:")
    print(f"    Runs: {rp['runs']}  Expected: {rp['expected_runs']:.1f}  "
          f"Z: {rp['z_score']:.4f}  p-value: {rp['p_value']:.4f}  "
          f"{'PASS ✓' if rp['pass'] else 'FAIL ✗'}")
    if not cp.get("skip"):
        print(f"  Chi-Squared Uniformity Test:")
        print(f"    χ²={cp['chi2']:.2f}  df={cp['dof']}  p-value={cp['p_value']:.4f}  "
              f"{'PASS ✓' if cp['pass'] else 'FAIL ✗'}")
    print(f"  Min-Entropy estimate: {Hp:.4f} bits/bit")
    print()
    print(f"  NOTE: PRNG MAY pass statistical tests but is NOT truly random.")
    print(f"        Its entire future output is determined by seed={42}.\n")

    # Determinism demo
    print_sep("PRNG Determinism Demo (same seed → same bits)")
    prng_determinism_demo(n_bits=32, seed=99999)
    print()

    # Comparison table
    print_sep("QRNG vs PRNG Comparison")
    rows = [
        ("Entropy source",      "Quantum measurement",    "Seed + deterministic algo"),
        ("Reproducible?",       "No — physically random", "Yes — given seed"),
        ("Predictable?",        "No (physics guarantee)", "Yes (seed known to attacker)"),
        ("Statistical tests",   "Pass (should)",          "Pass (well-designed PRNGs)"),
        ("NIST SP 800-90B",     "Certified (hardware)",   "Approved as DRBG (different std)"),
        ("Key material use",    "Ideal",                  "Acceptable with DRBG + seeding"),
        ("Seed required",       "No",                     "Yes (must be truly random seed)"),
        ("Hardware cost",       "Optical hardware",       "Software only"),
    ]
    print(f"  {'Feature':<28}  {'QRNG':>24}  {'PRNG':>28}")
    print(f"  {'-'*28}  {'-'*24}  {'-'*28}")
    for f, q, p in rows:
        print(f"  {f:<28}  {q:>24}  {p:>28}")

    print()
    print_sep("Key Takeaway")
    print("""
  QRNG is the gold standard for cryptographic key generation:
    - Entropy is physical, not algorithmic — no seed to steal or predict.
    - NIST SP 800-90B explicitly addresses hardware-based entropy sources.
    - Commercial QRNG devices: ID Quantique Quantis, Quside, Toshiba.

  PRNG (including /dev/urandom on Linux):
    - Uses hardware entropy sources to seed a DRBG (Deterministic RBG).
    - Secure for most purposes IF the seed is truly random and never reused.
    - Vulnerable if the seed is predicted or leaked (e.g., VM snapshot attacks).

  Quantum advantage in key generation:
    The same quantum hardware that performs QKD can also generate QRNG key material.
    Combined: quantum-secure key distribution AND quantum-secure key generation.
""")
    print_sep()


if __name__ == "__main__":
    main()
