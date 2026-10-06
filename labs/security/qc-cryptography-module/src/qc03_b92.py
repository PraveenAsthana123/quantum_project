"""
QC-03: B92 Two-State QKD Protocol
==================================
Algorithm  : B92 (Bennett 1992)
Reference  : C.H. Bennett, "Quantum cryptography using any two nonorthogonal
             states", Phys. Rev. Lett. 68, 3121 (1992).
Complexity : O(N) quantum channel uses; O(N) classical post-processing
Security   : Information-theoretic; guaranteed by non-orthogonality of states
Quantum Adv: Uses only 2 states (simpler hardware than BB84); non-orthogonality
             makes any measurement by Eve disturb the state detectably
"""

import time
import numpy as np

RNG = np.random.default_rng(seed=42)


def _b92_transmission(alice_bit: int, bob_basis: int,
                      eve_intercept: bool, rng: np.random.Generator) -> tuple[int, bool]:
    """
    B92 single qubit transmission.

    Alice encodes:
      bit=0 → |0⟩  (Z-basis +1 eigenstate)
      bit=1 → |+⟩  (X-basis +1 eigenstate)

    Bob's strategy (unambiguous state discrimination):
      To distinguish |0⟩ → measure in X basis; click if result is |-⟩ (bit=1)
        P(click | |0⟩, X) = |⟨-|0⟩|² = 0.5  → conclusive for bit=0
      To distinguish |+⟩ → measure in Z basis; click if result is |1⟩
        P(click | |+⟩, Z) = |⟨1|+⟩|² = 0.5  → conclusive for bit=1

    Overall detection efficiency ≈ 25% of all sent bits.

    Returns (decoded_bit, click) — click=True means Bob registered a detection.
    """
    if eve_intercept:
        # Eve measures in random basis, resends
        eve_basis = rng.integers(0, 2)
        # Eve's measurement probabilities (non-orthogonal state disturbs)
        if alice_bit == 0:   # |0⟩
            if eve_basis == 0:  # Z basis
                eve_result = 0  # deterministic: always |0⟩
            else:               # X basis: 50/50
                eve_result = rng.integers(0, 2)
                alice_bit = eve_result  # resend |+⟩ if 1, |0⟩ if 0
        else:                # |+⟩
            if eve_basis == 1:  # X basis
                eve_result = 0  # deterministic: always |+⟩
            else:               # Z basis: 50/50
                eve_result = rng.integers(0, 2)
                alice_bit = eve_result

    # Bob's measurement — uses his randomly chosen basis (0=Z, 1=X).
    # B92 click rule (unambiguous state discrimination):
    #   alice_bit=0 (|0⟩): click only when Bob chose X basis (basis=1)
    #                        and his X-basis result is |-⟩  → P(click)=0.5
    #   alice_bit=1 (|+⟩): click only when Bob chose Z basis (basis=0)
    #                        and his Z-basis result is |1⟩  → P(click)=0.5
    # Overall: P(click) = 0.5 (correct basis) × 0.5 (click) = 25%
    if alice_bit == 0 and bob_basis == 1:   # |0⟩, Bob uses X basis
        if rng.random() < 0.5:
            return 0, True   # conclusive: Alice sent bit 0
        return -1, False
    elif alice_bit == 1 and bob_basis == 0:  # |+⟩, Bob uses Z basis
        if rng.random() < 0.5:
            return 1, True   # conclusive: Alice sent bit 1
        return -1, False
    else:
        # Bob's basis is compatible with Alice's state → no information (no click)
        return -1, False


def simulate_b92(n_bits: int = 1000, eve_fraction: float = 0.0,
                 seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    alice_bits = rng.integers(0, 2, size=n_bits)
    bob_bases  = rng.integers(0, 2, size=n_bits)
    intercept_mask = rng.random(size=n_bits) < eve_fraction

    alice_key, bob_key = [], []
    n_clicks = 0

    for i in range(n_bits):
        decoded, click = _b92_transmission(
            int(alice_bits[i]), int(bob_bases[i]),
            bool(intercept_mask[i]), rng)
        if click:
            n_clicks += 1
            alice_key.append(int(alice_bits[i]))
            bob_key.append(decoded)

    # QBER on sifted key
    alice_arr = np.array(alice_key)
    bob_arr   = np.array(bob_key)
    errors = int((alice_arr != bob_arr).sum()) if len(alice_arr) > 0 else 0
    qber = errors / max(len(alice_arr), 1)

    return {
        "n_transmitted": n_bits,
        "n_sifted": n_clicks,
        "detection_efficiency": round(n_clicks / n_bits, 4),
        "qber": round(qber, 4),
        "eve_fraction": eve_fraction,
    }


def run_scenario() -> dict:
    t_start = time.perf_counter()

    r_no_eve  = simulate_b92(1000, 0.0, seed=42)
    r_partial = simulate_b92(1000, 0.25, seed=42)
    r_full    = simulate_b92(1000, 1.0, seed=42)

    # BB84 comparison (from qc01 logic, inline)
    # BB84 sifting ~50% vs B92 ~25% detection efficiency
    bb84_sift_rate = 0.50
    b92_detect_rate = r_no_eve["detection_efficiency"]

    elapsed = time.perf_counter() - t_start

    output = {
        "scenario_id": "QC-03",
        "algorithm": "B92",
        "sifted_bits_no_eve": r_no_eve["n_sifted"],
        "detection_efficiency_no_eve": r_no_eve["detection_efficiency"],
        "qber_no_eve": r_no_eve["qber"],
        "qber_partial_eve_25pct": r_partial["qber"],
        "qber_full_eve": r_full["qber"],
        "bb84_sift_rate": bb84_sift_rate,
        "b92_detect_rate": b92_detect_rate,
        "hardware_advantage": "B92 needs only 2 states vs 4 for BB84",
        "key_rate_penalty": f"{(1 - b92_detect_rate / bb84_sift_rate) * 100:.1f}% lower than BB84",
        "sim_time_ms": round(elapsed * 1000, 2),
        "security_model": "information-theoretic",
        "status": "PASS" if r_no_eve["qber"] < 0.05
                            and r_full["qber"] > 0.10 else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 65)
    print("QC-03  B92 — Two-State QKD Protocol")
    print("=" * 65)
    for k, v in results.items():
        print(f"  {k:<40} {v}")
    print()
    print("  Protocol Comparison (1000 qubits transmitted):")
    print(f"  {'Protocol':<12} {'States':<8} {'Sift/Detect':<14} "
          f"{'QBER (no Eve)':<16} {'Hardware'}")
    print("  " + "-" * 70)
    r = simulate_b92(1000, 0.0, seed=42)
    print(f"  {'BB84':<12} {'4':<8} {'~50%':<14} {'~0-1%':<16} {'2 bases, 4 states'}")
    print(f"  {'B92':<12} {'2':<8} {r['detection_efficiency']:<14.1%} "
          f"{r['qber']:<16.4f} {'2 states, simpler'}")
    print()
    print("  B92 QBER vs Eavesdropping:")
    print(f"  {'Eve fraction':<20} {'QBER':>8}  {'Detected?'}")
    print("  " + "-" * 40)
    for frac in [0.0, 0.25, 0.5, 1.0]:
        r = simulate_b92(1000, frac, seed=42)
        det = "YES (ABORT)" if r["qber"] > 0.08 else "NO"
        print(f"  {frac:<20} {r['qber']:>8.4f}  {det}")
    print("=" * 65)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
