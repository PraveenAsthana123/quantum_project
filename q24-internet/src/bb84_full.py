"""
Q24 — Quantum Internet
bb84_full.py

Full BB84 QKD with sifting, error estimation, error correction (Cascade),
and privacy amplification (hashing).

Reference: Bennett & Brassard (1984); Brassard & Salvail (1994) — Cascade;
           Bennett et al. (1995) — privacy amplification.

Outputs: data/bb84_full_results.json
"""

import hashlib
import json
import math
import os
import random


# ---------------------------------------------------------------------------
# Bit utilities
# ---------------------------------------------------------------------------

def random_bits(n: int) -> list:
    return [random.randint(0, 1) for _ in range(n)]


def xor_bits(a: list, b: list) -> list:
    return [x ^ y for x, y in zip(a, b)]


def parity(bits: list) -> int:
    return sum(bits) % 2


def hamming_distance(a: list, b: list) -> int:
    return sum(x != y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# BB84 transmission
# ---------------------------------------------------------------------------

def bb84_transmit(alice_bits: list, alice_bases: list,
                   bob_bases: list, qber: float,
                   seed: int = 42) -> list:
    """
    Simulate BB84 photon transmission.
    - Matching bases → Bob gets Alice's bit with error prob qber/2
    - Mismatching bases → Bob gets random bit
    Returns Bob's measured bits.
    """
    rng = random.Random(seed)
    bob_bits = []
    for ab, abase, bbase in zip(alice_bits, alice_bases, bob_bases):
        if abase == bbase:
            # Correct basis: channel noise introduces QBER
            if rng.random() < qber:
                bob_bits.append(1 - ab)  # bit flip
            else:
                bob_bits.append(ab)
        else:
            bob_bits.append(rng.randint(0, 1))  # random
    return bob_bits


def sift_key(bits: list, alice_bases: list, bob_bases: list) -> tuple:
    """Keep only positions where bases agree. Returns (alice_sifted, bob_sifted, indices)."""
    alice_sifted, bob_sifted, indices = [], [], []
    for i, (ab, bb) in enumerate(zip(alice_bases, bob_bases)):
        if ab == bb:
            alice_sifted.append(bits[i])
            bob_sifted.append(bits[i])  # placeholder; real is bob_bits
            indices.append(i)
    return alice_sifted, indices


def sift_key_full(alice_bits, bob_bits, alice_bases, bob_bases):
    alice_s, bob_s = [], []
    for ab, bb, a, b in zip(alice_bases, bob_bases, alice_bits, bob_bits):
        if ab == bb:
            alice_s.append(a)
            bob_s.append(b)
    return alice_s, bob_s


def estimate_qber(alice_sample: list, bob_sample: list) -> float:
    if not alice_sample:
        return 0.0
    errors = sum(a != b for a, b in zip(alice_sample, bob_sample))
    return errors / len(alice_sample)


# ---------------------------------------------------------------------------
# Cascade error correction (simplified single-pass binary parity check)
# ---------------------------------------------------------------------------

def cascade_correct(alice_key: list, bob_key: list,
                    qber_est: float) -> tuple:
    """
    Simplified Cascade error correction.
    Iterates through blocks of size k = ceil(0.73 / qber_est) and corrects
    single-bit errors using binary search on parity.

    Returns (corrected_bob_key, bits_disclosed).
    """
    if qber_est <= 0:
        return list(bob_key), 0

    n = len(alice_key)
    k = max(2, math.ceil(0.73 / qber_est))  # initial block size

    bob_corrected = list(bob_key)
    bits_disclosed = 0

    # Pass 1
    for start in range(0, n, k):
        block_a = alice_key[start:start + k]
        block_b = bob_corrected[start:start + k]
        if not block_a:
            break

        pa = parity(block_a)
        pb = parity(block_b)
        bits_disclosed += 1

        if pa != pb:
            # Binary search for the error
            lo, hi = start, min(start + k - 1, n - 1)
            while lo < hi:
                mid = (lo + hi) // 2
                sub_a = alice_key[lo:mid + 1]
                sub_b = bob_corrected[lo:mid + 1]
                bits_disclosed += 1
                if parity(sub_a) != parity(sub_b):
                    hi = mid
                else:
                    lo = mid + 1
            # Flip error bit
            if lo < n:
                bob_corrected[lo] = 1 - bob_corrected[lo]

    return bob_corrected, bits_disclosed


# ---------------------------------------------------------------------------
# Privacy amplification
# ---------------------------------------------------------------------------

def privacy_amplify(key: list, qber_est: float,
                     n_disclosed: int) -> tuple:
    """
    Privacy amplification via universal2 hashing (SHA-256 seeded).
    Shannon mutual info with Eve: I_e ≈ h(qber) per bit.
    Safe key length: l = n * (1 - h(qber)) - n_disclosed - security_param

    Returns (final_key_bits, security_level_str).
    """
    n = len(key)
    if n == 0:
        return [], "0 bits"

    def h2(p: float) -> float:
        if p <= 0 or p >= 1:
            return 0.0
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p)

    # Final key length
    mutual_info = h2(qber_est)
    safe_bits = max(0, int(n * (1.0 - mutual_info) - n_disclosed - 32))

    if safe_bits == 0:
        return [], "insufficient key material"

    # Hash the key to obtain the final secret key
    key_str = "".join(map(str, key)).encode()
    digest = hashlib.sha256(key_str).hexdigest()
    # Convert hex digest to bits
    all_bits = []
    for c in digest:
        val = int(c, 16)
        for bit_pos in range(3, -1, -1):
            all_bits.append((val >> bit_pos) & 1)

    final_key = all_bits[:min(safe_bits, len(all_bits))]
    security_level = f"{len(final_key)} bits, h(QBER)={mutual_info:.3f}"
    return final_key, security_level


# ---------------------------------------------------------------------------
# Full BB84 pipeline
# ---------------------------------------------------------------------------

def run_bb84(n_raw_bits: int = 10_000,
              qber: float = 0.05,
              seed: int = 42,
              sample_fraction: float = 0.1) -> dict:
    """
    Full BB84 pipeline: raw → sift → QBER estimate → Cascade → PA.
    """
    rng = random.Random(seed)

    # 1. Alice prepares
    alice_bits = [rng.randint(0, 1) for _ in range(n_raw_bits)]
    alice_bases = [rng.randint(0, 1) for _ in range(n_raw_bits)]  # 0=+, 1=×
    bob_bases = [rng.randint(0, 1) for _ in range(n_raw_bits)]

    # 2. Transmission
    bob_bits = bb84_transmit(alice_bits, alice_bases, bob_bases,
                              qber, seed=seed + 1)

    # 3. Sifting
    alice_sifted, bob_sifted = sift_key_full(
        alice_bits, bob_bits, alice_bases, bob_bases)
    n_sifted = len(alice_sifted)

    # 4. QBER estimation from a random sample
    n_sample = int(sample_fraction * n_sifted)
    rng2 = random.Random(seed + 2)
    sample_idx = sorted(rng2.sample(range(n_sifted), min(n_sample, n_sifted)))
    a_sample = [alice_sifted[i] for i in sample_idx]
    b_sample = [bob_sifted[i] for i in sample_idx]
    qber_est = estimate_qber(a_sample, b_sample)

    # Remove sample from working key
    remaining = [i for i in range(n_sifted) if i not in set(sample_idx)]
    alice_work = [alice_sifted[i] for i in remaining]
    bob_work = [bob_sifted[i] for i in remaining]

    # 5. Error correction (Cascade)
    bob_corrected, n_disclosed = cascade_correct(alice_work, bob_work, qber_est)
    n_errors_after = hamming_distance(alice_work, bob_corrected)

    # 6. Privacy amplification
    final_key, security_level = privacy_amplify(
        bob_corrected, qber_est, n_disclosed + n_sample)

    # Secret key rate (bits per raw photon)
    key_rate_bps = len(final_key) / (n_raw_bits / 1e6)  # bits per µs → Mbps

    print(f"Raw bits          : {n_raw_bits}")
    print(f"Sifted bits       : {n_sifted}")
    print(f"QBER (estimated)  : {qber_est:.4f} ({qber_est*100:.2f}%)")
    print(f"After correction  : {len(alice_work)} bits, {n_errors_after} errors remain")
    print(f"Final key bits    : {len(final_key)}")
    print(f"Key rate          : {key_rate_bps:.2f} kbps")
    print(f"Security level    : {security_level}")

    return {
        "raw_bits": n_raw_bits,
        "sifted_bits": n_sifted,
        "qber_pct": round(qber_est * 100, 3),
        "corrected_bits": len(alice_work),
        "residual_errors": n_errors_after,
        "final_key_bits": len(final_key),
        "key_rate_bps": round(key_rate_bps * 1000, 2),
        "security_level": security_level,
        "bits_disclosed_ec": n_disclosed,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Full BB84 QKD Simulation ===\n")

    results = run_bb84(n_raw_bits=10_000, qber=0.05)

    os.makedirs("data", exist_ok=True)
    out_path = "data/bb84_full_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
