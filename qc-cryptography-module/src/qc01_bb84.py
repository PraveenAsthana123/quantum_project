"""
QC-01: BB84 Quantum Key Distribution Protocol
==============================================
Algorithm  : BB84 (Bennett & Brassard, 1984)
Reference  : C.H. Bennett, G. Brassard, "Quantum cryptography: Public key
             distribution and coin tossing", Proc. IEEE ICCSSP, 1984.
Complexity : O(N) classical post-processing; O(N) quantum channel uses
Security   : Information-theoretic (unconditional) — IND-CPA secure against
             computationally unbounded adversaries
Quantum Adv: Eavesdropping detection via QBER; impossible to clone qubits
             (no-cloning theorem); security provably reduces to laws of physics
"""

import time
import hashlib
import os
import numpy as np

# ── Basis / State encoding ────────────────────────────────────────────────────
# Rectilinear (Z) basis: |0⟩ = 0, |1⟩ = 1
# Diagonal   (X) basis: |+⟩ = 0, |-⟩ = 1
Z_BASIS = 0
X_BASIS = 1

RNG = np.random.default_rng(seed=42)


def _measure_qubit(alice_bit: int, alice_basis: int,
                   bob_basis: int, eve_intercept: bool = False,
                   rng: np.random.Generator = None) -> tuple[int, int | None]:
    """
    Simulate one qubit travelling Alice → (Eve) → Bob.

    Returns (bob_result, eve_bit_or_None).
    Physics model:
      • Same basis  → perfect correlation
      • Different   → uniform random (quantum randomness)
      • Eve (intercept-resend): Eve measures in a random basis, resends
        her result; introduces 25% QBER when bases match
    """
    if rng is None:
        rng = RNG

    eve_bit = None
    transmitted_bit = alice_bit

    if eve_intercept:
        eve_basis = rng.integers(0, 2)
        if eve_basis == alice_basis:
            eve_bit = alice_bit
        else:
            eve_bit = rng.integers(0, 2)
            transmitted_bit = eve_bit  # Eve resends in her random basis

    # Bob measures
    if bob_basis == alice_basis:
        bob_result = transmitted_bit
    else:
        bob_result = rng.integers(0, 2)

    return bob_result, eve_bit


def simulate_bb84(n_bits: int = 1000, eve_fraction: float = 0.0,
                  seed: int = 42) -> dict:
    """
    Full BB84 simulation.

    Parameters
    ----------
    n_bits       : number of qubits Alice sends
    eve_fraction : fraction of qubits Eve intercepts (0.0 = no Eve,
                   1.0 = intercept every qubit)
    seed         : RNG seed for reproducibility

    Returns
    -------
    dict with keys: sifted_bits, qber, final_key_bits, final_key
    """
    rng = np.random.default_rng(seed)

    alice_bits   = rng.integers(0, 2, size=n_bits)
    alice_bases  = rng.integers(0, 2, size=n_bits)
    bob_bases    = rng.integers(0, 2, size=n_bits)

    bob_results = np.zeros(n_bits, dtype=int)
    eve_bits    = np.full(n_bits, -1, dtype=int)
    intercept_mask = rng.random(size=n_bits) < eve_fraction

    for i in range(n_bits):
        br, eb = _measure_qubit(
            int(alice_bits[i]), int(alice_bases[i]), int(bob_bases[i]),
            eve_intercept=bool(intercept_mask[i]), rng=rng)
        bob_results[i] = br
        if eb is not None:
            eve_bits[i] = eb

    # Sifting: keep positions where bases match
    sift_mask = alice_bases == bob_bases
    sifted_alice = alice_bits[sift_mask]
    sifted_bob   = bob_results[sift_mask]
    n_sifted     = int(sift_mask.sum())

    # QBER estimation on a random sample (use 20% of sifted)
    n_sample = max(1, n_sifted // 5)
    sample_idx = rng.choice(n_sifted, size=n_sample, replace=False)
    errors = int((sifted_alice[sample_idx] != sifted_bob[sample_idx]).sum())
    qber = errors / n_sample

    # Remaining sifted key (exclude sample used for QBER check)
    remaining_mask = np.ones(n_sifted, dtype=bool)
    remaining_mask[sample_idx] = False
    raw_key_alice = sifted_alice[remaining_mask]
    raw_key_bob   = sifted_bob[remaining_mask]

    # Privacy amplification: final_key_len = sifted_len − 2*error_count
    total_errors = int((raw_key_alice != raw_key_bob).sum())
    pa_len = max(0, len(raw_key_alice) - 2 * total_errors)

    # Hash-based privacy amplification (SHA-256 based shortening)
    if pa_len > 0:
        seed_bytes = raw_key_alice[:pa_len].tobytes()
        digest = hashlib.sha256(seed_bytes).digest()
        # Convert digest to bit array, truncate to pa_len
        digest_bits = np.unpackbits(np.frombuffer(digest, dtype=np.uint8))
        final_key = digest_bits[:min(pa_len, len(digest_bits))]
        pa_len = len(final_key)
    else:
        final_key = np.array([], dtype=np.uint8)

    return {
        "n_transmitted": n_bits,
        "n_sifted": n_sifted,
        "sift_ratio": n_sifted / n_bits,
        "qber": round(qber, 4),
        "total_errors": total_errors,
        "final_key_bits": pa_len,
        "final_key_hex": final_key[:64].tobytes().hex() if pa_len >= 8 else "",
        "eve_fraction": eve_fraction,
    }


def _ecdh_timing() -> float:
    """Approximate ECDH P-256 key generation time via pure-Python timing proxy."""
    t0 = time.perf_counter()
    # Simulate ECDH cost: two large modular exponentiations (scalar mult proxy)
    p = (1 << 256) - 2**224 + 2**192 + 2**96 - 1  # P-256 prime
    for _ in range(100):
        x = pow(int.from_bytes(os.urandom(32), "big") % p, p - 1, p)
    elapsed = time.perf_counter() - t0
    return elapsed


def run_scenario() -> dict:
    """Run all BB84 sub-scenarios and return consolidated results."""
    t_start = time.perf_counter()

    results_no_eve       = simulate_bb84(n_bits=1000, eve_fraction=0.0, seed=42)
    results_partial_eve  = simulate_bb84(n_bits=1000, eve_fraction=0.25, seed=42)
    results_full_eve     = simulate_bb84(n_bits=1000, eve_fraction=1.0, seed=42)

    t_bb84 = time.perf_counter() - t_start

    t_ecdh_start = time.perf_counter()
    _ecdh_timing()
    t_ecdh = time.perf_counter() - t_ecdh_start

    output = {
        "scenario_id": "QC-01",
        "algorithm": "BB84",
        "sifted_bits": results_no_eve["n_sifted"],
        "qber_no_eve": results_no_eve["qber"],
        "qber_partial_eve_25pct": results_partial_eve["qber"],
        "qber_full_eve": results_full_eve["qber"],
        "final_key_bits_no_eve": results_no_eve["final_key_bits"],
        "final_key_bits_full_eve": results_full_eve["final_key_bits"],
        "bb84_sim_time_ms": round(t_bb84 * 1000, 2),
        "classical_equiv": "ECDH P-256",
        "classical_sim_time_ms": round(t_ecdh * 1000, 2),
        "security_model": "information-theoretic",
        "quantum_advantage": "Eavesdropping detectable via QBER; no-cloning theorem",
        "status": "PASS" if results_no_eve["qber"] < 0.05
                           and results_full_eve["qber"] > 0.15 else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 60)
    print("QC-01  BB84 — Quantum Key Distribution Protocol")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k:<35} {v}")
    print()
    print("  Eve-scenario QBER summary:")
    print(f"  {'Scenario':<25} {'QBER':>8}  {'Eve detected?'}")
    print("  " + "-" * 50)
    for label, eve_frac in [("No Eve", 0.0), ("25% Eve", 0.25), ("100% Eve", 1.0)]:
        r = simulate_bb84(1000, eve_frac, seed=42)
        detected = "YES (ABORT)" if r["qber"] > 0.11 else "NO"
        print(f"  {label:<25} {r['qber']:>8.4f}  {detected}")
    print()
    print("  Classical comparison:")
    print(f"  {'Scheme':<20} {'Security':<25} {'Quantum-safe?'}")
    print("  " + "-" * 60)
    print(f"  {'BB84':<20} {'Information-theoretic':<25} {'Yes (physical laws)'}")
    print(f"  {'ECDH P-256':<20} {'Computational (128-bit)':<25} {'No (Shor breaks ECC)'}")
    print(f"  {'DH-2048':<20} {'Computational (112-bit)':<25} {'No (Shor breaks DL)'}")
    print("=" * 60)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
