"""
QC-04: BBM92 — Entanglement-Based BB84
=======================================
Algorithm  : BBM92 (Bennett, Brassard, Mermin 1992)
Reference  : C.H. Bennett, G. Brassard, N.D. Mermin, "Quantum cryptography
             without Bell's theorem", Phys. Rev. Lett. 68, 557 (1992).
Complexity : O(N) measurements; same key rate as BB84 (~50% sifting)
Security   : Equivalent to BB84; security based on quantum correlations of
             entangled pairs, not preparation of individual qubits by Alice
Quantum Adv: Neither party needs to prepare qubits; both just measure;
             source can be untrusted (but not proven device-independent)
"""

import time
import numpy as np

RNG = np.random.default_rng(seed=42)


def _generate_bell_pair(rng: np.random.Generator) -> tuple[int, int]:
    """
    Sample |Φ+⟩ = (|00⟩ + |11⟩)/√2.
    Returns (alice_qubit_value, bob_qubit_value) in Z basis before measurement.
    The pair has perfect Z-basis and X-basis correlations.
    """
    base_bit = rng.integers(0, 2)
    return int(base_bit), int(base_bit)   # perfect Z-basis correlation


def _measure_bell_qubit(qubit_val: int, basis: int,
                        rng: np.random.Generator) -> int:
    """
    Measure a qubit (prepared in |0⟩ or |1⟩) in given basis.
    Z basis (0): identity — result = qubit_val
    X basis (1): Hadamard transform, then Z — P(0)=P(1)=0.5 if qubit is |0⟩/|1⟩,
                 but for an entangled pair both parties get same result.
    """
    if basis == 0:  # Z basis
        return qubit_val
    else:           # X basis: Hadamard + Z
        # For a Bell pair |Φ+⟩ measured in XX, both get correlated results
        # Model: both get the same uniformly random bit
        return rng.integers(0, 2)


def simulate_bbm92(n_pairs: int = 1000, eve_fraction: float = 0.0,
                   seed: int = 42) -> dict:
    """
    BBM92 simulation.

    A source distributes |Φ+⟩ pairs. Alice and Bob each independently choose
    a random basis (Z or X) and measure their qubit.

    Correlations:
      ZZ → Alice and Bob always agree (key bit)
      XX → Alice and Bob always agree (key bit)
      ZX or XZ → uncorrelated (discarded during sifting)

    Eve model: intercept-resend on fraction of pairs.
    """
    rng = np.random.default_rng(seed)

    alice_bases = rng.integers(0, 2, size=n_pairs)
    bob_bases   = rng.integers(0, 2, size=n_pairs)
    intercept   = rng.random(size=n_pairs) < eve_fraction

    alice_key, bob_key = [], []

    for i in range(n_pairs):
        a_qubit, b_qubit = _generate_bell_pair(rng)

        if intercept[i]:
            # Eve intercepts: measures both in random basis, resends separable state
            eve_basis = rng.integers(0, 2)
            # After Eve's measurement, qubits collapse; she resends product states
            eve_a = _measure_bell_qubit(a_qubit, eve_basis, rng)
            eve_b = _measure_bell_qubit(b_qubit, eve_basis, rng)
            a_result = _measure_bell_qubit(eve_a, alice_bases[i], rng)
            b_result = _measure_bell_qubit(eve_b, bob_bases[i], rng)
        else:
            # Genuine Bell pair measurement
            a_result = _measure_bell_qubit(a_qubit, alice_bases[i], rng)
            if alice_bases[i] == bob_bases[i]:
                # Same basis: perfect correlation from entanglement
                b_result = a_result
            else:
                b_result = rng.integers(0, 2)

        # Sifting: keep only when bases match
        if alice_bases[i] == bob_bases[i]:
            alice_key.append(a_result)
            bob_key.append(b_result)

    alice_arr = np.array(alice_key)
    bob_arr   = np.array(bob_key)
    errors = int((alice_arr != bob_arr).sum()) if len(alice_arr) > 0 else 0
    qber = errors / max(len(alice_arr), 1)
    sifted = len(alice_arr)
    final_key_len = max(0, sifted - 2 * errors)

    return {
        "n_pairs": n_pairs,
        "n_sifted": sifted,
        "sift_ratio": round(sifted / n_pairs, 4),
        "errors": errors,
        "qber": round(qber, 4),
        "final_key_bits": final_key_len,
        "eve_fraction": eve_fraction,
    }


def run_scenario() -> dict:
    t_start = time.perf_counter()

    r_no_eve  = simulate_bbm92(1000, 0.0, seed=42)
    r_partial = simulate_bbm92(1000, 0.25, seed=42)
    r_full    = simulate_bbm92(1000, 1.0, seed=42)

    elapsed = time.perf_counter() - t_start

    output = {
        "scenario_id": "QC-04",
        "algorithm": "BBM92",
        "sifted_bits_no_eve": r_no_eve["n_sifted"],
        "sift_ratio": r_no_eve["sift_ratio"],
        "qber_no_eve": r_no_eve["qber"],
        "qber_partial_eve_25pct": r_partial["qber"],
        "qber_full_eve": r_full["qber"],
        "final_key_no_eve": r_no_eve["final_key_bits"],
        "final_key_full_eve": r_full["final_key_bits"],
        "vs_bb84_diff": "Same key rate; Alice need not prepare qubits",
        "source_trust": "Source can be untrusted (attacks detectable via QBER)",
        "sim_time_ms": round(elapsed * 1000, 2),
        "security_model": "information-theoretic (equivalent to BB84)",
        "status": "PASS" if r_no_eve["qber"] < 0.05
                            and r_full["qber"] > 0.15 else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 65)
    print("QC-04  BBM92 — Entanglement-Based BB84")
    print("=" * 65)
    for k, v in results.items():
        print(f"  {k:<42} {v}")
    print()
    print("  BB84 vs BBM92 comparison:")
    print(f"  {'Property':<35} {'BB84':<20} {'BBM92'}")
    print("  " + "-" * 70)
    rows = [
        ("Qubit preparation", "Alice prepares", "Source distributes"),
        ("Parties measure", "Alice prepares, Bob measures", "Both measure"),
        ("Sifting efficiency", "~50%", "~50%"),
        ("Security basis", "Uncertainty principle", "Quantum correlations"),
        ("Source trust", "Alice trusted", "Source may be untrusted"),
        ("Device-independent?", "No", "No (need E91 for that)"),
    ]
    for prop, bb84, bbm92 in rows:
        print(f"  {prop:<35} {bb84:<20} {bbm92}")
    print()
    print("  QBER scenarios:")
    print(f"  {'Eve fraction':<20} {'QBER':>8}  {'Final key bits':>15}  {'Status'}")
    print("  " + "-" * 55)
    for frac in [0.0, 0.25, 0.5, 1.0]:
        r = simulate_bbm92(1000, frac, seed=42)
        status = "SECURE" if r["qber"] < 0.11 else "ABORT"
        print(f"  {frac:<20} {r['qber']:>8.4f}  {r['final_key_bits']:>15}  {status}")
    print("=" * 65)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
