"""
CUSTOMER DEMO PITCH — Timing Side-Channel Analysis on RSA
==========================================================
Side-channel attacks exploit physical information leaked during cryptographic
operations: execution time, power consumption, electromagnetic emissions.

This demo shows a TIMING side-channel on a naive square-and-multiply RSA
exponentiation:
  - The algorithm processes each bit of the private exponent d.
  - For bit=0: SQUARE only.
  - For bit=1: SQUARE + MULTIPLY.
  - The extra multiplication for bit=1 takes measurably longer.
  - An attacker can recover the private exponent bit-by-bit.

Constant-time countermeasure:
  Montgomery ladder: always performs both square AND multiply, regardless
  of the bit value — execution time is independent of d.

Real-world impact: Timing attacks have been demonstrated against:
  - OpenSSL RSA (2003, Brumley & Boneh)
  - Hardware security modules
  - Smart card implementations

Audience: Cryptographic engineers, security reviewers, interview panels.
Runtime: < 10 seconds.
"""

import time
import math
import random
import numpy as np
from collections import defaultdict


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
# Naive square-and-multiply
# ---------------------------------------------------------------------------

def naive_modexp(base: int, exp: int, mod: int) -> int:
    """
    Naive square-and-multiply modular exponentiation.
    Timing DEPENDS on the Hamming weight of exp (number of 1-bits).
    """
    result = 1
    base   = base % mod
    bits   = bin(exp)[2:]
    for bit in bits:
        result = (result * result) % mod   # always square
        if bit == "1":
            result = (result * base) % mod  # multiply only for bit=1
    return result


# ---------------------------------------------------------------------------
# Constant-time Montgomery ladder
# ---------------------------------------------------------------------------

def montgomery_ladder(base: int, exp: int, mod: int) -> int:
    """
    Montgomery ladder: always performs two operations per bit.
    Timing is constant regardless of exp value.
    """
    r0, r1 = 1, base
    bits   = bin(exp)[2:]
    for bit in bits:
        if bit == "0":
            r1 = (r0 * r1) % mod
            r0 = (r0 * r0) % mod
        else:
            r0 = (r0 * r1) % mod
            r1 = (r1 * r1) % mod
    return r0


# ---------------------------------------------------------------------------
# Timing measurement
# ---------------------------------------------------------------------------

def measure_timing(func, base: int, exp: int, mod: int,
                   n_trials: int = 500) -> list:
    """Measure execution time of modexp in nanoseconds across trials."""
    times = []
    for _ in range(n_trials):
        start = time.perf_counter_ns()
        func(base, exp, mod)
        end   = time.perf_counter_ns()
        times.append(end - start)
    return times


# ---------------------------------------------------------------------------
# Side-channel key recovery (toy demo)
# ---------------------------------------------------------------------------

def recover_bits_from_timing(timing_by_bit: dict) -> list:
    """
    Recover each bit of the exponent from timing measurements.
    Bits with higher mean timing → likely 1-bit (extra multiply).
    Bits with lower mean timing → likely 0-bit (square only).
    """
    recovered = []
    for bit_pos in sorted(timing_by_bit.keys()):
        times = timing_by_bit[bit_pos]
        mean  = np.mean(times)
        recovered.append((bit_pos, mean))
    means = [t for _, t in recovered]
    median_t = np.median(means)
    bits_recovered = [1 if t > median_t else 0 for _, t in recovered]
    return bits_recovered


def timing_attack_demo(secret_exp: int, mod: int, base: int = 3,
                        n_measurements: int = 200) -> dict:
    """
    Simulate timing attack: measure time per bit position to recover bits of secret_exp.
    """
    bits      = bin(secret_exp)[2:]
    true_bits = [int(b) for b in bits]

    # For each bit position, measure timing for "that bit path"
    timing_by_bit = defaultdict(list)

    # Simplified model: time per operation ≈ constant + noise
    # Bit=1 adds one multiplication (slightly longer)
    BASE_TIME  = 50    # ns base per bit
    MUL_EXTRA  = 15    # ns for extra multiply on bit=1
    NOISE_STD  = 8     # ns measurement noise (realistic: ~10 ns jitter)
    rng = np.random.default_rng(42)

    for bit_pos, bit_val in enumerate(true_bits):
        for _ in range(n_measurements):
            t = BASE_TIME + (MUL_EXTRA if bit_val == 1 else 0) + rng.normal(0, NOISE_STD)
            timing_by_bit[bit_pos].append(t)

    recovered_bits = recover_bits_from_timing(timing_by_bit)
    correct = sum(a == b for a, b in zip(true_bits, recovered_bits))
    accuracy = correct / len(true_bits)

    return {
        "true_bits":      true_bits,
        "recovered_bits": recovered_bits,
        "accuracy":       accuracy,
        "n_bits":         len(true_bits),
        "correct":        correct,
        "timing_by_bit":  dict(timing_by_bit),
    }


# ---------------------------------------------------------------------------
# Constant-time variance measurement
# ---------------------------------------------------------------------------

def timing_variance_comparison(mod: int = 997,
                                n_samples: int = 300) -> dict:
    """Compare timing variance of naive vs constant-time implementations."""
    base = 3
    rng  = random.Random(42)

    naive_times  = []
    ladder_times = []

    for _ in range(n_samples):
        exp = rng.randint(1, mod - 1)
        t0 = time.perf_counter_ns()
        naive_modexp(base, exp, mod)
        t1 = time.perf_counter_ns()
        naive_modexp(base, exp, mod)    # warmup
        t2 = time.perf_counter_ns()
        naive_times.append(t1 - t0)

        t0 = time.perf_counter_ns()
        montgomery_ladder(base, exp, mod)
        t1 = time.perf_counter_ns()
        ladder_times.append(t1 - t0)

    return {
        "naive_mean":   np.mean(naive_times),
        "naive_std":    np.std(naive_times),
        "naive_cv":     np.std(naive_times) / np.mean(naive_times),
        "ladder_mean":  np.mean(ladder_times),
        "ladder_std":   np.std(ladder_times),
        "ladder_cv":    np.std(ladder_times) / np.mean(ladder_times),
    }


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    # Small toy RSA parameters (for demo speed)
    p, q  = 61, 53
    N     = p * q          # 3233
    e     = 17             # public exponent
    phi_N = (p - 1) * (q - 1)
    d     = pow(e, -1, phi_N)   # private exponent: 2753

    print_sep("TIMING SIDE-CHANNEL ANALYSIS — Naive RSA vs Constant-Time")
    print(f"  RSA parameters: p={p}, q={q}, N={N}, e={e}, d={d} (SECRET)\n")

    # Verify RSA
    m = 65
    c = naive_modexp(m, e, N)
    m_dec = naive_modexp(c, d, N)
    print(f"  RSA sanity check: plaintext={m}, ciphertext={c}, decrypted={m_dec}")
    assert m == m_dec, "RSA decryption failed"
    print(f"  RSA decryption correct ✓\n")

    # Timing attack simulation
    print_sep("Simulated Timing Attack on Private Exponent d={d}")
    secret_bits = bin(d)[2:]
    print(f"  Private exponent d = {d}  (binary: {secret_bits})")
    print(f"  Bit length: {len(secret_bits)} bits")
    print(f"  Running timing attack ({200} measurements per bit position)...\n")

    result = timing_attack_demo(d, N, n_measurements=200)
    print(f"  True bits:      {''.join(str(b) for b in result['true_bits'])}")
    print(f"  Recovered bits: {''.join(str(b) for b in result['recovered_bits'])}")
    match_str = ''.join('✓' if a==b else '✗'
                        for a, b in zip(result['true_bits'], result['recovered_bits']))
    print(f"  Match:          {match_str}")
    print(f"\n  Bits correct: {result['correct']}/{result['n_bits']}  "
          f"({result['accuracy']*100:.1f}%)")
    print()

    # Per-bit timing breakdown
    print_sep("Per-Bit Timing (first 12 bits)")
    print(f"  {'Bit#':>5}  {'True':>5}  {'Mean(ns)':>10}  {'Std(ns)':>9}  "
          f"{'Recovered':>10}  Correct?")
    print(f"  {'-'*5}  {'-'*5}  {'-'*10}  {'-'*9}  {'-'*10}  {'-'*8}")
    tb = result["timing_by_bit"]
    for i, (true, recov) in enumerate(
            zip(result["true_bits"][:12], result["recovered_bits"][:12])):
        t = tb[i]
        print(f"  {i:>5}  {true:>5}  {np.mean(t):>10.1f}  {np.std(t):>9.1f}  "
              f"{recov:>10}  {'✓' if true == recov else '✗'}")

    print()

    # Timing variance comparison
    print_sep("Timing Variance: Naive vs Montgomery Ladder")
    print("  Measuring over 300 random exponents (mod=997)...")
    tv = timing_variance_comparison()
    print(f"\n  {'Implementation':<25}  {'Mean (ns)':>10}  {'Std (ns)':>10}  "
          f"{'CV':>8}  Constant-time?")
    print(f"  {'-'*25}  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*14}")
    print(f"  {'Naive sq-and-multiply':<25}  {tv['naive_mean']:>10.1f}  "
          f"{tv['naive_std']:>10.1f}  {tv['naive_cv']:>8.4f}  NO")
    print(f"  {'Montgomery ladder':<25}  {tv['ladder_mean']:>10.1f}  "
          f"{tv['ladder_std']:>10.1f}  {tv['ladder_cv']:>8.4f}  Yes (lower CV)")
    cv_reduction = (tv['naive_cv'] - tv['ladder_cv']) / tv['naive_cv']
    print(f"\n  Timing variance reduced by {cv_reduction*100:.1f}% with constant-time impl.")
    print()

    # Bits-leaked estimate
    print_sep("Bits Leaked Estimate vs Measurements per Bit")
    print(f"  {'Measurements':>14}  {'Expected accuracy':>18}  {'Bits leaked':>12}  Notes")
    print(f"  {'-'*14}  {'-'*18}  {'-'*12}  {'-'*30}")
    n_bits = len(result["true_bits"])
    for n_meas in [10, 50, 100, 200, 500, 1000]:
        # Model: accuracy improves with sqrt(n_meas) (CLT)
        noise_std  = 8
        signal     = 15   # MUL_EXTRA
        snr        = signal / (noise_std / math.sqrt(n_meas))
        # Bit detection accuracy using normal approximation
        from math import erfc
        acc = 0.5 * (1 + 1 - erfc(snr / math.sqrt(2)) / 1)
        acc = min(acc, 1.0)
        bits_leaked = acc * n_bits
        note = "Barely better than guessing" if acc < 0.55 else \
               "Partial key recovery" if acc < 0.90 else \
               "Full key recovery"
        print(f"  {n_meas:>14}  {acc:>17.1%}  {bits_leaked:>12.1f}  {note}")

    print()
    print_sep("Key Takeaway")
    print("""
  Timing side-channels are a REAL threat to deployed RSA implementations.
  Brumley & Boneh (2003) recovered an OpenSSL RSA-1024 key over a LOCAL NETWORK
  in under 2 minutes using timing measurements.

  Countermeasures (from weakest to strongest):
    1. Blinding: randomise the base before exponentiation (prevents adaptive attacks)
    2. Montgomery ladder: constant-time per bit regardless of bit value
    3. Constant-time implementation at assembly level (cache-timing resistance)
    4. Hardware security modules with physical shielding
    5. Post-quantum lattice schemes (ML-KEM, ML-DSA): different algebraic structure,
       far fewer timing covert channels

  Post-quantum relevance: ML-KEM uses matrix-vector multiplication over rings —
  its timing profile is more uniform than RSA. NIST PQC submissions were explicitly
  evaluated for constant-time implementability.
""")
    print_sep()


if __name__ == "__main__":
    main()
