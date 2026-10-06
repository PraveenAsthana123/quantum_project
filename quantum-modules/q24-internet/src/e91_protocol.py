"""
Q24 — Quantum Internet
e91_protocol.py

E91 (Ekert 1991) QKD using entangled Bell pairs.
Alice and Bob choose random measurement bases.
CHSH inequality violation detects eavesdropping.
Compares key rate vs BB84.

Reference: Ekert, PRL 67, 661 (1991);
           Clauser, Horne, Shimony, Holt (1969) — CHSH inequality.

Outputs: data/e91_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# Bell state and measurement
# ---------------------------------------------------------------------------

def bell_pair_state() -> tuple:
    """
    Generate a |Φ+> = (|00> + |11>) / √2 Bell pair.
    Returns (alice_hidden_bit, bob_hidden_bit) drawn from the entangled dist.
    """
    # Simulate measurement: both get the same random bit (for matching bases)
    hidden = random.randint(0, 1)
    return hidden, hidden


def measure_qubit(hidden_bit: int, basis_angle_deg: float,
                  partner_basis_deg: float = None,
                  is_alice: bool = True,
                  qber: float = 0.0) -> int:
    """
    Project qubit onto measurement basis at angle θ.
    For a |Φ+> state, P(same result | bases a,b) = cos²((a-b)/2).
    Simplified: if bases agree → same result; else random.
    """
    if random.random() < qber:
        return 1 - hidden_bit  # noise flip
    return hidden_bit


def correlation(a1: float, a2: float) -> float:
    """
    Quantum correlation <A_a B_b> = -cos(a - b) for singlet |Ψ->
    or cos(a-b) for |Φ+>.
    """
    delta_rad = math.radians(a1 - a2)
    return math.cos(delta_rad)


# ---------------------------------------------------------------------------
# CHSH parameter
# ---------------------------------------------------------------------------

def chsh_value(e_ab: float, e_ab2: float,
               e_a2b: float, e_a2b2: float) -> float:
    """
    S = |E(a,b) - E(a,b') + E(a',b) + E(a',b')|
    Classical bound: |S| ≤ 2
    Quantum maximum (Tsirelson): |S| ≤ 2√2 ≈ 2.828
    """
    return abs(e_ab - e_ab2 + e_a2b + e_a2b2)


def chsh_theoretical(a_angles: list, b_angles: list) -> float:
    """
    Compute CHSH using ideal quantum correlations for |Φ+>.
    a_angles: Alice's two measurement angles [degrees]
    b_angles: Bob's two measurement angles [degrees]
    """
    e_ab   = correlation(a_angles[0], b_angles[0])
    e_ab2  = correlation(a_angles[0], b_angles[1])
    e_a2b  = correlation(a_angles[1], b_angles[0])
    e_a2b2 = correlation(a_angles[1], b_angles[1])
    return chsh_value(e_ab, e_ab2, e_a2b, e_a2b2)


# ---------------------------------------------------------------------------
# E91 simulation
# ---------------------------------------------------------------------------

# Standard E91 measurement angles
ALICE_ANGLES = [0.0, 45.0]          # a1=0°, a2=45°
BOB_ANGLES   = [22.5, 67.5]         # b1=22.5°, b2=67.5°
KEY_BASES    = {"Alice": 45.0, "Bob": 45.0}  # shared basis for key bits


def simulate_e91(n_pairs: int = 10_000,
                  qber: float = 0.02,
                  eve_present: bool = False,
                  seed: int = 42) -> dict:
    """
    E91 protocol simulation.
    - Alice and Bob each randomly choose from 3 measurement angles.
    - Correlations on non-key bases → CHSH test.
    - Matching key bases → raw key bits.

    Returns performance dict.
    """
    random.seed(seed)

    # Extended angle sets (E91 uses 3 angles each)
    alice_angles = [0.0, 45.0, 90.0]
    bob_angles   = [22.5, 67.5, 112.5]
    # Key sifting: Alice 45°, Bob 67.5° → correlation angle 22.5°

    results_a, results_b, bases_a, bases_b = [], [], [], []

    for _ in range(n_pairs):
        a_idx = random.randint(0, 2)
        b_idx = random.randint(0, 2)
        theta_a = alice_angles[a_idx]
        theta_b = bob_angles[b_idx]

        # Generate |Φ+> = (|00>+|11>)/√2:
        # P(Alice=0) = 0.5; conditioned on Alice=0, P(Bob=0|bases_match)=1
        # For general angle difference δ = θ_a - θ_b:
        # P(A=0, B=0) = cos²(δ/2)/2;  P(A=1, B=1) = cos²(δ/2)/2
        # P(A=0, B=1) = sin²(δ/2)/2;  P(A=1, B=0) = sin²(δ/2)/2
        delta_rad = math.radians(theta_a - theta_b)
        p_same = math.cos(delta_rad / 2.0) ** 2  # P(same outcome)

        alice_bit = random.randint(0, 1)

        # Eavesdropper: collapses entanglement → random outcomes (QBER→50%)
        eff_qber = qber + (0.25 if eve_present else 0.0)

        # Bob's outcome: correlated with Alice's by quantum mechanics
        if random.random() < eff_qber:
            bob_bit = random.randint(0, 1)  # error / eavesdropper
        else:
            # Quantum correlation: same with prob p_same, different with 1-p_same
            if random.random() < p_same:
                bob_bit = alice_bit
            else:
                bob_bit = 1 - alice_bit

        results_a.append(alice_bit)
        results_b.append(bob_bit)
        bases_a.append(a_idx)
        bases_b.append(b_idx)

    # --- CHSH test (use bases 0,1 for Alice, 0,1 for Bob) ---
    def empirical_correlation(a_idx: int, b_idx: int) -> float:
        a_vals, b_vals = [], []
        for i in range(n_pairs):
            if bases_a[i] == a_idx and bases_b[i] == b_idx:
                a_vals.append(2 * results_a[i] - 1)   # {0,1} → {-1,+1}
                b_vals.append(2 * results_b[i] - 1)
        if not a_vals:
            return 0.0
        return sum(a * b for a, b in zip(a_vals, b_vals)) / len(a_vals)

    e00 = empirical_correlation(0, 0)
    e01 = empirical_correlation(0, 1)
    e10 = empirical_correlation(1, 0)
    e11 = empirical_correlation(1, 1)
    S = abs(e00 - e01 + e10 + e11)

    # Theoretical CHSH for these angles
    S_theory = chsh_theoretical(alice_angles[:2], bob_angles[:2])

    # Key sifting: both choose angle index 1 (45° for Alice, 67.5° for Bob)
    # For |Φ+>: correlated outcomes (not anti-correlated), so no flip needed.
    key_a, key_b = [], []
    for i in range(n_pairs):
        if bases_a[i] == 1 and bases_b[i] == 1:
            key_a.append(results_a[i])
            key_b.append(results_b[i])  # |Φ+>: same outcomes in same basis

    n_key = len(key_a)
    n_errors = sum(a != b for a, b in zip(key_a, key_b))
    qber_measured = n_errors / n_key if n_key > 0 else 0.0

    # Secret key rate (after simple one-way error correction + PA)
    def h2(p):
        if p <= 0 or p >= 1:
            return 0.0
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p)

    rate_fraction = max(0.0, 1.0 - 2 * h2(qber_measured))
    n_final_key = int(n_key * rate_fraction)
    key_rate_bps = n_final_key / (n_pairs / 1e6)

    # Classical bound: S ≤ 2.  Violation of S > 2 confirms no eavesdropper.
    # If S ≤ 2 → local hidden variable model possible → Eve detected.
    eve_detected = S <= 2.0

    print(f"Bell pairs        : {n_pairs}")
    print(f"CHSH value S      : {S:.4f}  (theory: {S_theory:.4f})")
    print(f"CHSH threshold    : 2√2 = {2*math.sqrt(2):.4f}")
    print(f"Eve detected      : {eve_detected}")
    print(f"Key bits (sifted) : {n_key}")
    print(f"QBER measured     : {qber_measured*100:.2f}%")
    print(f"Final key bits    : {n_final_key}")
    print(f"Key rate          : {key_rate_bps:.2f} kbps")

    return {
        "bell_pairs": n_pairs,
        "chsh_value": round(S, 4),
        "chsh_theoretical": round(S_theory, 4),
        "chsh_threshold": round(2.0 * math.sqrt(2), 4),
        "eve_detected": bool(S <= 2.0),
        "key_bits": n_key,
        "final_key_bits": n_final_key,
        "key_rate_bps": round(key_rate_bps * 1000, 2),
        "qber_measured_pct": round(qber_measured * 100, 3),
        "eve_present_simulated": eve_present,
    }


# ---------------------------------------------------------------------------
# Compare E91 vs BB84 key rate
# ---------------------------------------------------------------------------

def compare_e91_bb84(n_pairs: int = 10_000, qber: float = 0.02) -> dict:
    """
    Compare secret key fraction for E91 and BB84 at the same QBER.
    """
    def h2(p):
        if p <= 0 or p >= 1:
            return 0.0
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p)

    # E91: ~1/9 of pairs in key basis (random angle choice from 3)
    e91_sifting = 1.0 / 9.0
    e91_secret_fraction = e91_sifting * max(0.0, 1.0 - 2 * h2(qber))

    # BB84: 50% sifting, then 1-h(QBER) secret fraction
    bb84_sifting = 0.5
    bb84_secret_fraction = bb84_sifting * max(0.0, 1.0 - h2(qber))

    return {
        "qber": qber,
        "e91_sifting_fraction": e91_sifting,
        "e91_secret_key_fraction": round(e91_secret_fraction, 4),
        "bb84_sifting_fraction": bb84_sifting,
        "bb84_secret_key_fraction": round(bb84_secret_fraction, 4),
        "bb84_advantage_factor": round(
            bb84_secret_fraction / max(e91_secret_fraction, 1e-12), 2),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== E91 (Ekert 1991) QKD Simulation ===\n")

    # Normal operation
    results = simulate_e91(n_pairs=10_000, qber=0.02, eve_present=False)

    print("\n--- E91 vs BB84 comparison ---")
    comparison = compare_e91_bb84(n_pairs=10_000, qber=0.02)
    print(f"E91 secret key fraction : {comparison['e91_secret_key_fraction']:.4f}")
    print(f"BB84 secret key fraction: {comparison['bb84_secret_key_fraction']:.4f}")
    print(f"BB84 advantage          : {comparison['bb84_advantage_factor']:.1f}x")

    # Eve simulation
    print("\n--- With eavesdropper ---")
    results_eve = simulate_e91(n_pairs=10_000, qber=0.02, eve_present=True, seed=99)

    results["comparison_vs_bb84"] = comparison
    results["with_eve"] = {
        "chsh_value": results_eve["chsh_value"],
        "eve_detected": results_eve["eve_detected"],
        "qber_measured_pct": results_eve["qber_measured_pct"],
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/e91_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
