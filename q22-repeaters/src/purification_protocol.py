"""
Q22 — Quantum Repeaters
purification_protocol.py

DEJMPS entanglement purification protocol (double selection).
Start from Werner states with fidelity F=0.8 and apply 3 rounds.
Tracks fidelity improvement, pairs consumed, and success probabilities.

Reference: Deutsch et al., PRL 77, 2818 (1996) — DEJMPS protocol.

Outputs: data/purification_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# Werner state representation
# ---------------------------------------------------------------------------

def werner_state(f: float) -> dict:
    """
    Werner state: rho = F|Φ+><Φ+| + (1-F)/4 * I
    Parameterised by singlet fraction F ∈ [0.25, 1].
    Returns a dict with diagonal elements in the Bell basis.
    """
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"Fidelity must be in [0,1], got {f}")
    return {
        "F_phiplus": f,
        "F_phiminus": (1.0 - f) / 3.0,
        "F_psiplus":  (1.0 - f) / 3.0,
        "F_psiminus": (1.0 - f) / 3.0,
    }


def fidelity_from_state(state: dict) -> float:
    return state["F_phiplus"]


# ---------------------------------------------------------------------------
# DEJMPS purification step
# ---------------------------------------------------------------------------

def dejmps_step(state: dict) -> tuple:
    """
    Apply one DEJMPS purification round to two copies of 'state'.

    For a Werner state parameterised by F (singlet fraction):
      p_success = F^2 + (1-F)^2/9 * 5 + ...
    The closed-form result (Briegel et al. 1998 notation):

      Let A = F,  B = C = D = (1-F)/3

      p_success = A^2 + B^2 + ... (bilateral XOR measurement)
      Simplified for Werner: p_succ = A^2 + (1-A)^2/9*(1+4+4/9+...)

    We use the standard BBPSSW / DEJMPS result for Werner states:
      p_succ = F^2 + (5/9)(1-F)^2 + (2/3)(2F(1-F)/3 + ...)
    Exact formula (Deutsch 1996, eq. 8 simplified for Werner input):
      p_succ = [F + (1-F)/3]^2 / ...

    Most rigorous closed form (see Sangouard 2011):
      p_succ = A^2 + B^2 + 2*(A+B)*(C+D) where A,B,C,D are Bell-basis probs
             = F^2 + ((1-F)/3)^2 + 2*(F+(1-F)/3)*2*(1-F)/3
    But for Werner: B=C=D=(1-F)/3

      p_succ = F^2 + 3*((1-F)/3)^2 + ...

    We use the derivation that gives the known F_out formula:
      F_out = (F^2 + (1/9)(1-F)^2) / p_succ
      p_succ = F^2 + (5/9)(1-F)^2 + (4/9)*2*F*(1-F)

    Returns (new_state, p_success, pairs_consumed_per_output).
    """
    f = fidelity_from_state(state)

    # DEJMPS for Werner states (Deutsch et al. 1996, eq. derived for Werner)
    # Let A = F (prob of |Φ+>), and B=C=D=(1-F)/3 (other Bell components).
    # After bilateral XOR (CNOT) the parity check succeeds with:
    #   p_succ = A^2 + B^2 + C^2 + D^2 + 2*(A*D + B*C)
    # For Werner state (B=C=D=(1-F)/3):
    #   p_succ = F^2 + 3*((1-F)/3)^2 + 2*(F*(1-F)/3 + ((1-F)/3)^2)
    # This simplifies to: p_succ = (F^2 + (1/9)(1-F)^2 + (2/3)(1-F)F + (2/9)(1-F)^2)
    # The standard closed-form result (Briegel 1998 notation):
    #   p_succ = F^2 + (5/9)(1-F)^2 + (4F(1-F)/3)   ← incorrect variant
    # Correct result per Deutsch 1996 for Werner states (also Bennett 1996):
    #   F_out = (F^2 + (1-F)^2/9) / p_succ
    #   p_succ = F^2 + (2/3)*F*(1-F) + (5/9)*(1-F)^2  [corrected]
    p_succ = (f ** 2
              + (2.0 / 3.0) * f * (1.0 - f)
              + (5.0 / 9.0) * (1.0 - f) ** 2)

    if p_succ < 1e-12:
        return state, 0.0, 2

    # Output fidelity (Bennett 1996 / Deutsch 1996):
    f_out = (f ** 2 + (1.0 / 9.0) * (1.0 - f) ** 2) / p_succ
    f_out = min(1.0, max(0.25, f_out))

    new_state = werner_state(f_out)
    return new_state, p_succ, 2  # always consumes 2 pairs per output pair


# ---------------------------------------------------------------------------
# Multi-round purification
# ---------------------------------------------------------------------------

def run_purification(initial_fidelity: float = 0.8,
                      n_rounds: int = 3) -> dict:
    """
    Apply n_rounds of DEJMPS purification starting from a Werner state.
    Tracks fidelity after each round, pairs consumed, and success probs.
    """
    state = werner_state(initial_fidelity)

    fidelities = [initial_fidelity]
    success_probs = []
    pairs_per_output_pairs = []
    cumulative_pairs = [1.0]  # start with 1 "virtual" pair

    current_pairs_needed = 1.0  # pairs needed to produce one output pair

    for rnd in range(1, n_rounds + 1):
        new_state, p_succ, pairs_per_step = dejmps_step(state)

        if p_succ < 1e-12:
            print(f"Round {rnd}: purification failed (p_succ ≈ 0), stopping.")
            break

        current_pairs_needed = current_pairs_needed * pairs_per_step / p_succ
        fidelities.append(fidelity_from_state(new_state))
        success_probs.append(round(p_succ, 6))
        pairs_per_output_pairs.append(round(current_pairs_needed, 2))
        cumulative_pairs.append(round(current_pairs_needed, 2))
        state = new_state

        print(f"Round {rnd}: F = {fidelities[-1]:.5f}  "
              f"p_succ = {p_succ:.4f}  "
              f"pairs/output = {current_pairs_needed:.2f}")

    return {
        "initial_fidelity": initial_fidelity,
        "rounds": n_rounds,
        "output_fidelities": [round(f, 6) for f in fidelities],
        "pairs_consumed": pairs_per_output_pairs,
        "success_probabilities": success_probs,
        "final_fidelity": round(fidelities[-1], 6),
        "total_pairs_for_one_output": round(current_pairs_needed, 2),
    }


# ---------------------------------------------------------------------------
# Sensitivity analysis: starting fidelity sweep
# ---------------------------------------------------------------------------

def fidelity_sweep(f_values=None, n_rounds: int = 3) -> list:
    """Run purification for a range of initial fidelities."""
    if f_values is None:
        f_values = [0.7, 0.75, 0.8, 0.85, 0.9]

    sweep = []
    for f0 in f_values:
        state = werner_state(f0)
        f_cur = f0
        for _ in range(n_rounds):
            new_state, p_succ, _ = dejmps_step(state)
            if p_succ < 1e-12:
                break
            state = new_state
            f_cur = fidelity_from_state(state)
        sweep.append({
            "initial_fidelity": f0,
            "final_fidelity": round(f_cur, 6),
            "improvement": round(f_cur - f0, 6),
        })
    return sweep


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== DEJMPS Entanglement Purification Protocol ===\n")

    results = run_purification(initial_fidelity=0.8, n_rounds=3)

    print(f"\nInitial fidelity : {results['initial_fidelity']:.4f}")
    print(f"Final fidelity   : {results['final_fidelity']:.5f}")
    print(f"Pairs per output : {results['total_pairs_for_one_output']:.2f}")

    # Fidelity sweep
    print("\n--- Fidelity improvement sweep (3 rounds) ---")
    sweep = fidelity_sweep(n_rounds=3)
    for row in sweep:
        print(f"  F0={row['initial_fidelity']:.2f} → "
              f"F_out={row['final_fidelity']:.5f}  "
              f"(+{row['improvement']:.4f})")

    results["fidelity_sweep"] = sweep

    os.makedirs("data", exist_ok=True)
    out_path = "data/purification_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
