"""
Q03 — Magic State Distillation.

Demonstrates T-gate magic state |A⟩ = T|+⟩ preparation and the
15-to-1 distillation protocol (simplified numerical simulation).

The 15-to-1 protocol (Bravyi & Kitaev 2005):
  - 15 noisy |A⟩ states (each with error probability ε)
  - Output: 1 state with error probability ~35ε³

Saves results to data/magic_state_results.json.
"""

import json
import math
from pathlib import Path

import numpy as np

RESULTS_PATH = Path(__file__).parent.parent / "data" / "magic_state_results.json"

RNG = np.random.default_rng(42)

# ── Magic state definition ────────────────────────────────────────────────
# T gate: |0⟩ → |0⟩,  |1⟩ → e^{iπ/4}|1⟩
# Magic state |A⟩ = T|+⟩ = (|0⟩ + e^{iπ/4}|1⟩) / √2

def ideal_magic_state() -> np.ndarray:
    """Return the ideal T-gate magic state |A⟩ = (|0⟩ + e^{iπ/4}|1⟩)/√2."""
    phase = np.exp(1j * math.pi / 4)
    return np.array([1.0, phase], dtype=complex) / math.sqrt(2)


def noisy_magic_state(epsilon: float) -> np.ndarray:
    """
    Return a noisy version of the magic state.
    With probability ε, apply Z error (phase flip) to the magic state.
    ρ_noisy = (1-ε)|A⟩⟨A| + ε Z|A⟩⟨A|Z
    """
    ideal = ideal_magic_state()
    Z = np.array([1., -1.])  # Z eigenvalues acting on amplitudes
    noisy_sv = ideal.copy()
    noisy_sv[1] *= -1  # Z|A⟩: flip phase of |1⟩ amplitude
    dm_ideal = np.outer(ideal, ideal.conj())
    dm_err = np.outer(noisy_sv, noisy_sv.conj())
    return (1 - epsilon) * dm_ideal + epsilon * dm_err


def fidelity_with_ideal(dm: np.ndarray) -> float:
    """Compute F = ⟨A|ρ|A⟩."""
    ideal = ideal_magic_state()
    return float(np.real(ideal.conj() @ dm @ ideal))


# ── 15-to-1 distillation (Bravyi-Kitaev) ─────────────────────────────────
# Exact analytic formula for output error probability:
#   ε_out ≈ 35 * ε_in³  (for small ε_in)
# The protocol:
#   1. Prepare 15 noisy |A⟩ states.
#   2. Encode in the [[15,1,3]] Reed-Muller code.
#   3. Measure stabilizers; accept only if all stabilizer outcomes are +1.
#   4. Decode the one remaining logical qubit as the distilled state.
# We simulate this by the analytic output error formula + Monte Carlo sampling.

def distill_15_to_1_analytic(epsilon_in: float) -> float:
    """
    Analytic output error for 15-to-1 protocol (leading order):
      ε_out = 35 * ε_in^3
    """
    return 35.0 * epsilon_in ** 3


def distill_5_to_1_analytic(epsilon_in: float) -> float:
    """
    Analytic output error for 5-to-1 protocol (simplified):
      ε_out ≈ 10 * ε_in^2
    """
    return 10.0 * epsilon_in ** 2


def simulate_distillation_15_to_1_mc(epsilon_in: float, n_trials: int = 100_000) -> dict:
    """
    Monte Carlo simulation of 15-to-1 distillation.

    For each trial:
    - Draw 15 Bernoulli(ε_in) error flags for the 15 input states.
    - The protocol succeeds (not rejected) if the total parity of errors satisfies
      the acceptance condition (simplified: accept if the even-weight code check passes).
    - Post-selection: among accepted trials, count how often an output error occurs.

    Simplified model: the Reed-Muller [[15,1,3]] code can correct any 1-qubit
    error among the 15, so an output error occurs only if ≥3 of the 15 inputs
    are erroneous (minimum-weight uncorrectable error pattern).
    """
    accepted = 0
    output_errors = 0

    for _ in range(n_trials):
        errors = RNG.random(15) < epsilon_in  # which of 15 states have Z error
        n_err = int(errors.sum())

        # Simplified acceptance: accept if ≤ 14 errors (reject only all-15-error)
        # (Full protocol rejects specific error patterns via stabilizer checks)
        # Better approximation: reject if total weight is odd (parity check)
        if n_err % 2 == 1:
            continue  # rejected by parity post-selection (50% overhead simplified)

        accepted += 1
        # Output error occurs if ≥3 correlated errors defeat the code (d=3 code)
        # Exact condition: any 3+ errors of specific weight pattern
        if n_err >= 3:
            output_errors += 1

    p_accept = accepted / n_trials if n_trials > 0 else 0
    p_out_error = output_errors / accepted if accepted > 0 else 0

    return {
        "trials": n_trials,
        "accepted": accepted,
        "p_accept": round(p_accept, 6),
        "output_errors": output_errors,
        "p_output_error": round(p_out_error, 8),
    }


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Q03 — Magic State Distillation (T-gate |A⟩)")
    print("=" * 60)

    epsilon_in = 0.05  # 5% input error rate
    print(f"\n  Input magic state error rate: ε_in = {epsilon_in}")

    # Ideal magic state
    ideal = ideal_magic_state()
    dm_ideal = np.outer(ideal, ideal.conj())
    print(f"\n  Ideal |A⟩ = (|0⟩ + e^{{iπ/4}}|1⟩)/√2")
    print(f"  Ideal state fidelity with itself: {fidelity_with_ideal(dm_ideal):.6f}")

    # Noisy input state
    dm_noisy = noisy_magic_state(epsilon_in)
    f_in = fidelity_with_ideal(dm_noisy)
    print(f"\n  Noisy input fidelity: F_in = {f_in:.6f}  (error = {1-f_in:.4f})")

    # 15-to-1 distillation (analytic)
    eps_out_15 = distill_15_to_1_analytic(epsilon_in)
    eps_out_5 = distill_5_to_1_analytic(epsilon_in)
    f_out_15 = 1.0 - eps_out_15
    f_out_5 = 1.0 - eps_out_5
    print(f"\n  15-to-1 distillation:")
    print(f"    ε_out = 35 * ε_in³ = 35 * {epsilon_in}³ = {eps_out_15:.6f}")
    print(f"    Output fidelity F_out = {f_out_15:.6f}")
    print(f"    Overhead: 15 input states → 1 output state")
    print(f"\n  5-to-1 simplified protocol:")
    print(f"    ε_out ≈ 10 * ε_in² = {eps_out_5:.6f}")
    print(f"    Output fidelity F_out = {f_out_5:.6f}")

    # Monte Carlo verification
    print(f"\nRunning Monte Carlo simulation (15-to-1, {100_000} trials)...")
    mc_result = simulate_distillation_15_to_1_mc(epsilon_in, n_trials=100_000)
    print(f"  MC output error rate: {mc_result['p_output_error']:.6f}")
    print(f"  Analytic prediction : {eps_out_15:.6f}")
    print(f"  Acceptance rate     : {mc_result['p_accept']:.4f}")

    # Input fidelity sweep
    eps_sweep = [0.01, 0.02, 0.05, 0.10]
    print("\n  Input ε → Output ε (15-to-1 analytic):")
    fidelity_improvement = []
    for e in eps_sweep:
        e_out = distill_15_to_1_analytic(e)
        print(f"    ε_in={e:.2f} → ε_out={e_out:.6f}  (improvement: {e/max(e_out,1e-12):.1f}×)")
        fidelity_improvement.append({"epsilon_in": e, "epsilon_out": round(e_out, 8),
                                     "improvement_factor": round(e / max(e_out, 1e-12), 2)})

    data = {
        "protocol": "15-to-1 Reed-Muller magic state distillation",
        "magic_state": "|A> = T|+> = (|0> + exp(i*pi/4)|1>)/sqrt(2)",
        "input_fidelity": round(f_in, 8),
        "output_fidelity_15to1": round(f_out_15, 8),
        "output_fidelity_5to1": round(f_out_5, 8),
        "input_error_rate": epsilon_in,
        "output_error_rate_analytic": round(eps_out_15, 8),
        "output_error_rate_mc": mc_result["p_output_error"],
        "distillation_overhead": 15,
        "mc_acceptance_rate": mc_result["p_accept"],
        "formula": "eps_out = 35 * eps_in^3",
        "fidelity_improvement_sweep": fidelity_improvement,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
