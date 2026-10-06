"""
QC-02: E91 (Ekert 91) Entanglement-Based QKD
=============================================
Algorithm  : E91 (Artur Ekert, 1991)
Reference  : A.K. Ekert, "Quantum cryptography based on Bell's theorem",
             Phys. Rev. Lett. 67, 661 (1991).
Complexity : O(N) measurements; O(N) classical post-processing
Security   : Device-independent security foundation via Bell-inequality test
Quantum Adv: Security certified by CHSH inequality violation (S > 2 quantum,
             |S| ≤ 2 classical); entanglement guarantees no local hidden variables
"""

import time
import numpy as np

RNG = np.random.default_rng(seed=42)

# Alice's measurement angles (radians)
ALICE_ANGLES = [0.0, np.pi / 4, np.pi / 2]          # 0°, 45°, 90°
# Bob's measurement angles
BOB_ANGLES   = [np.pi / 4, np.pi / 2, 3 * np.pi / 4]  # 45°, 90°, 135°


def _bell_pair() -> tuple[int, int]:
    """Sample a |Φ+⟩ = (|00⟩+|11⟩)/√2 Bell pair (perfect correlations)."""
    bit = RNG.integers(0, 2)
    return int(bit), int(bit)   # perfect correlation in Z basis


def _measure_spin(bit: int, angle: float, rng: np.random.Generator) -> int:
    """
    Measure a qubit prepared in |0⟩ or |1⟩ at a detector angle θ.

    P(+1 | |0⟩, θ) = cos²(θ/2)
    P(+1 | |1⟩, θ) = sin²(θ/2)
    Returns ±1 outcome.
    """
    if bit == 0:
        p_plus = np.cos(angle / 2) ** 2
    else:
        p_plus = np.sin(angle / 2) ** 2
    return 1 if rng.random() < p_plus else -1


def _quantum_correlation(a_angle: float, b_angle: float) -> float:
    """Theoretical quantum correlation: E(a,b) = -cos(a - b)."""
    return -np.cos(a_angle - b_angle)


def simulate_e91(n_pairs: int = 500, eve_mode: str = "none",
                 seed: int = 42) -> dict:
    """
    E91 simulation.

    eve_mode : "none" | "full" | "partial"
      none    → genuine entanglement, expect S ≈ 2√2 ≈ 2.828
      full    → Eve breaks entanglement, replaces with classical corr (S ≈ 2.0)
      partial → Eve intercepts 50% of pairs (S ≈ 2.4)
    """
    rng = np.random.default_rng(seed)

    # Storage: correlation accumulators for 9 angle combinations
    correlation_sums  = {}
    correlation_counts = {}
    for a in ALICE_ANGLES:
        for b in BOB_ANGLES:
            correlation_sums[(a, b)]   = 0.0
            correlation_counts[(a, b)] = 0

    key_bits = []

    for _ in range(n_pairs):
        a_angle = ALICE_ANGLES[rng.integers(0, 3)]
        b_angle = BOB_ANGLES[rng.integers(0, 3)]

        if eve_mode == "none":
            # |Φ+⟩ entangled pair: Alice's outcome is uniformly +1/-1;
            # Bob's result is correlated via E(a,b) = -cos(a-b).
            # Implementation: Alice picks ±1 uniformly; Bob's outcome is
            # set so that product a_out*b_out = -cos(a-b) in expectation.
            a_out = 1 if rng.random() < 0.5 else -1
            # P(b_out = a_out) = cos²((a-b)/2)  [for |Φ+⟩]
            p_same = np.cos((a_angle - b_angle) / 2) ** 2
            b_out = a_out if rng.random() < p_same else -a_out
        elif eve_mode == "full":
            # Eve breaks entanglement: classical hidden-variable (LHV) model
            # Max LHV CHSH is 2.0 — use uniform random independent outcomes
            a_out = 1 if rng.random() < 0.5 else -1
            b_out = 1 if rng.random() < 0.5 else -1
        else:  # partial — 50% quantum, 50% classical
            if rng.random() < 0.5:
                a_out = 1 if rng.random() < 0.5 else -1
                p_same = np.cos((a_angle - b_angle) / 2) ** 2
                b_out = a_out if rng.random() < p_same else -a_out
            else:
                a_out = 1 if rng.random() < 0.5 else -1
                b_out = 1 if rng.random() < 0.5 else -1

        correlation_sums[(a_angle, b_angle)]   += a_out * b_out
        correlation_counts[(a_angle, b_angle)] += 1

        # Key extraction: only when Alice uses 0° or 90° AND Bob uses 90°
        # (matching compatible angle pair for key bits)
        if abs(a_angle - b_angle) < 1e-9 or abs(abs(a_angle - b_angle) - np.pi / 2) < 1e-9:
            if a_out == b_out:
                key_bits.append(1 if a_out == 1 else 0)

    # Compute observed correlations
    E = {}
    for pair, s in correlation_sums.items():
        c = correlation_counts[pair]
        E[pair] = s / c if c > 0 else 0.0

    # CHSH: S = E(0, π/4) - E(0, 3π/4) + E(π/2, π/4) + E(π/2, 3π/4)
    S = (E[(0.0, np.pi / 4)]
         - E[(0.0, 3 * np.pi / 4)]
         + E[(np.pi / 2, np.pi / 4)]
         + E[(np.pi / 2, 3 * np.pi / 4)])

    # Theoretical CHSH values:
    S_theory_no_eve  = 2 * np.sqrt(2)  # ≈ 2.828
    S_theory_full    = 2.0
    S_classical_bound = 2.0

    quantum_violation = abs(S) > S_classical_bound + 0.05
    eve_detected = not quantum_violation

    return {
        "n_pairs": n_pairs,
        "eve_mode": eve_mode,
        "chsh_score_S": round(S, 4),
        "chsh_quantum_bound": round(S_theory_no_eve, 4),
        "chsh_classical_bound": S_classical_bound,
        "quantum_violation": quantum_violation,
        "eve_detected": eve_detected,
        "key_bits_extracted": len(key_bits),
        "key_efficiency": round(len(key_bits) / n_pairs, 4),
    }


def run_scenario() -> dict:
    t_start = time.perf_counter()

    r_no_eve  = simulate_e91(n_pairs=500, eve_mode="none",    seed=42)
    r_full    = simulate_e91(n_pairs=500, eve_mode="full",    seed=42)
    r_partial = simulate_e91(n_pairs=500, eve_mode="partial", seed=42)

    elapsed = time.perf_counter() - t_start

    output = {
        "scenario_id": "QC-02",
        "algorithm": "E91 (Ekert 91)",
        "chsh_no_eve": r_no_eve["chsh_score_S"],
        "chsh_full_eve": r_full["chsh_score_S"],
        "chsh_partial_eve": r_partial["chsh_score_S"],
        "quantum_bound": r_no_eve["chsh_quantum_bound"],
        "classical_bound": r_no_eve["chsh_classical_bound"],
        "key_bits_no_eve": r_no_eve["key_bits_extracted"],
        "key_bits_full_eve": r_full["key_bits_extracted"],
        "security_verified_no_eve": r_no_eve["quantum_violation"],
        "security_broken_full_eve": r_full["eve_detected"],
        "sim_time_ms": round(elapsed * 1000, 2),
        "security_model": "device-independent (Bell-inequality based)",
        "quantum_advantage": "CHSH violation certifies no local hidden-variable model",
        "status": "PASS" if (r_no_eve["chsh_score_S"] > 2.7
                             and r_full["chsh_score_S"] <= 2.1) else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 65)
    print("QC-02  E91 — Entanglement-Based QKD (Bell Test)")
    print("=" * 65)
    for k, v in results.items():
        print(f"  {k:<40} {v}")

    print()
    print("  CHSH Summary (|S| ≤ 2 classical, |S| ≤ 2√2≈2.828 quantum):")
    print(f"  {'Eve Scenario':<20} {'S (observed)':>13}  {'Quantum?':<8}  {'Eve detected?'}")
    print("  " + "-" * 60)
    for mode, label in [("none", "No Eve"), ("partial", "50% Eve"), ("full", "Full Eve")]:
        r = simulate_e91(500, mode, seed=42)
        q = "YES" if r["quantum_violation"] else "NO"
        ed = "NO" if r["quantum_violation"] else "YES (ABORT)"
        print(f"  {label:<20} {r['chsh_score_S']:>13.4f}  {q:<8}  {ed}")
    print()
    print("  Theoretical correlations E(a,b) = -cos(a-b):")
    print(f"  {'Angle pair':<20} {'Theory':>10}  {'Classical HV max':>17}")
    print("  " + "-" * 50)
    for a_deg, b_deg in [(0, 45), (0, 135), (90, 45), (90, 135)]:
        a, b = np.radians(a_deg), np.radians(b_deg)
        e_q = _quantum_correlation(a, b)
        print(f"  ({a_deg}°,{b_deg}°){'':<13} {e_q:>10.4f}  {'bounded by ±1':>17}")
    print("=" * 65)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
