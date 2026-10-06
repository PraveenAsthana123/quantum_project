"""
Randomized Benchmarking (RB)
==============================
Generates random Clifford sequences of increasing lengths and measures
the survival probability under depolarizing noise.

Protocol:
1. Choose a random sequence of m Clifford gates C_1, ..., C_m
2. Append the inverse: C_{m+1} = (C_m · ... · C_1)^{-1}
3. Measure survival probability: P(|0⟩ after applying all m+1 gates)
4. Repeat over many random sequences; average survival probability

Expected decay: F(m) = A · p^m + B
where:
    p  = 1 - (d²-1)/d² · r  (depolarizing parameter)
    r  = error per gate
    d  = 2 (qubit dimension)
    A, B depend on SPAM errors

Extracts: error per Clifford (EPC) = (1-p)(d-1)/d for d=2: EPC = (1-p)/2

Saves results to data/rb_results.json.
"""

import json
import numpy as np
from pathlib import Path
from scipy.optimize import curve_fit


# ---------------------------------------------------------------------------
# Single-qubit Clifford group (24 elements)
# ---------------------------------------------------------------------------

# Generate the 24 single-qubit Clifford gates as SU(2) matrices
def _generate_cliffords() -> list:
    """Generate all 24 single-qubit Clifford matrices."""
    X  = np.array([[0, 1], [1, 0]], dtype=complex)
    Y  = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z  = np.array([[1, 0], [0, -1]], dtype=complex)
    I2 = np.eye(2, dtype=complex)
    H  = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    S  = np.array([[1, 0], [0, 1j]], dtype=complex)
    Sd = np.array([[1, 0], [0, -1j]], dtype=complex)

    generators = [I2, X, Y, Z, H, S, Sd,
                  H @ S, H @ Sd, S @ H, Sd @ H,
                  S @ H @ S, Sd @ H @ Sd,
                  H @ S @ H, H @ Sd @ H,
                  S @ H @ S @ H, Sd @ H @ Sd @ H,
                  H @ S @ H @ S, H @ Sd @ H @ Sd,
                  S @ H @ S @ H @ S, Sd @ H @ Sd @ H @ Sd,
                  X @ H, Y @ H, Z @ H]

    # Deduplicate by matrix comparison
    cliffords = []
    for g in generators:
        is_dup = False
        for c in cliffords:
            if np.allclose(g, c, atol=1e-10) or np.allclose(g, -c, atol=1e-10):
                is_dup = True
                break
        if not is_dup:
            cliffords.append(g)
        if len(cliffords) == 24:
            break

    # Pad if needed
    while len(cliffords) < 24:
        cliffords.append(I2.copy())

    return cliffords[:24]


CLIFFORDS = _generate_cliffords()


def random_clifford_sequence(m: int, rng: np.random.Generator) -> list:
    """Generate a random sequence of m Clifford gate indices."""
    return rng.integers(0, 24, size=m).tolist()


def sequence_inverse(seq_indices: list) -> np.ndarray:
    """Compute the inverse (recovery) gate for a Clifford sequence."""
    U = np.eye(2, dtype=complex)
    for idx in seq_indices:
        U = CLIFFORDS[idx] @ U
    return U.conj().T  # inverse = conjugate transpose for unitary


# ---------------------------------------------------------------------------
# Noise model: depolarizing channel
# ---------------------------------------------------------------------------

def depolarizing_channel(rho: np.ndarray, error_rate: float) -> np.ndarray:
    """
    Apply single-qubit depolarizing channel:
        E(ρ) = (1-3p/4)ρ + p/4·(XρX + YρY + ZρZ)
    where error_rate = p (probability of any error).
    """
    I2 = np.eye(2, dtype=complex)
    X  = np.array([[0, 1], [1, 0]], dtype=complex)
    Y  = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z  = np.array([[1, 0], [0, -1]], dtype=complex)

    p = error_rate
    return ((1 - 3 * p / 4) * rho
            + (p / 4) * (X @ rho @ X + Y @ rho @ Y + Z @ rho @ Z))


def apply_gate_with_noise(rho: np.ndarray, gate: np.ndarray,
                           error_rate: float) -> np.ndarray:
    """Apply gate U then depolarizing noise."""
    rho_after_gate = gate @ rho @ gate.conj().T
    return depolarizing_channel(rho_after_gate, error_rate)


# ---------------------------------------------------------------------------
# RB survival probability simulation
# ---------------------------------------------------------------------------

def run_rb_sequence(seq_indices: list, error_rate: float) -> float:
    """
    Simulate one RB sequence:
    1. Start in |0⟩
    2. Apply m random Cliffords with noise
    3. Apply recovery gate with noise
    4. Return probability of measuring |0⟩
    """
    # Initial state |0⟩⟨0|
    rho = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)
    proj0 = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)

    # Apply random Clifford sequence
    for idx in seq_indices:
        gate = CLIFFORDS[idx]
        rho = apply_gate_with_noise(rho, gate, error_rate)

    # Apply recovery gate (inverse of sequence product)
    recovery = sequence_inverse(seq_indices)
    rho = apply_gate_with_noise(rho, recovery, error_rate)

    # Survival probability: P(|0⟩)
    return float(np.real(np.trace(proj0 @ rho)))


def run_rb_experiment(sequence_lengths: list, error_rate: float,
                       n_sequences: int = 30, seed: int = 42) -> dict:
    """
    Run full RB experiment: average survival probability over many random sequences
    for each sequence length.
    """
    rng = np.random.default_rng(seed)
    survival_probs = []

    for m in sequence_lengths:
        probs = []
        for _ in range(n_sequences):
            seq = random_clifford_sequence(m, rng)
            p = run_rb_sequence(seq, error_rate)
            probs.append(p)
        survival_probs.append(float(np.mean(probs)))

    return {"sequence_lengths": sequence_lengths, "survival_probs": survival_probs}


# ---------------------------------------------------------------------------
# Exponential decay fit: F(m) = A * p^m + B
# ---------------------------------------------------------------------------

def rb_decay_model(m, A, p, B):
    return A * (p ** m) + B


def fit_rb_decay(sequence_lengths: list, survival_probs: list) -> dict:
    """Fit RB data to exponential decay and extract EPC."""
    try:
        popt, pcov = curve_fit(
            rb_decay_model,
            sequence_lengths,
            survival_probs,
            p0=[0.5, 0.99, 0.5],
            bounds=([0, 0, 0], [1, 1, 1]),
            maxfev=5000,
        )
        A, p, B = popt
        perr = np.sqrt(np.diag(pcov))

        # Error per Clifford: EPC = (1-p)(d-1)/d for d=2
        d = 2
        epc = (1 - p) * (d - 1) / d
        gate_fidelity = 1 - epc

        return {
            "A": round(float(A), 6),
            "decay_rate_p": round(float(p), 8),
            "B": round(float(B), 6),
            "epc": round(float(epc), 8),
            "gate_fidelity": round(float(gate_fidelity), 8),
            "fit_errors": perr.tolist(),
            "fit_success": True,
        }
    except Exception as e:
        return {"fit_success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Randomized Benchmarking (RB)")
    print("=" * 60)

    sequence_lengths = [1, 2, 4, 8, 16, 32]
    n_sequences = 50
    error_rates_to_test = [0.001, 0.005, 0.01, 0.02]

    print(f"\nSequence lengths : {sequence_lengths}")
    print(f"Sequences/length : {n_sequences}")
    print(f"Clifford group   : 24 single-qubit gates\n")

    all_rb_results = []
    for error_rate in error_rates_to_test:
        rb_data = run_rb_experiment(sequence_lengths, error_rate, n_sequences)
        fit = fit_rb_decay(sequence_lengths, rb_data["survival_probs"])

        print(f"Error rate {error_rate:.4f}:")
        print(f"  Survival probs: {[round(p, 4) for p in rb_data['survival_probs']]}")
        if fit["fit_success"]:
            print(f"  Fitted EPC     : {fit['epc']:.6f}")
            print(f"  Gate fidelity  : {fit['gate_fidelity']:.6f}")
            print(f"  Decay rate p   : {fit['decay_rate_p']:.6f}")

        all_rb_results.append({
            "input_error_rate": error_rate,
            "survival_probs": [round(p, 6) for p in rb_data["survival_probs"]],
            **fit,
        })

    # Primary result (middle error rate)
    primary = all_rb_results[1]

    results = {
        "sequence_lengths": sequence_lengths,
        "n_sequences_per_length": n_sequences,
        "n_clifford_gates": len(CLIFFORDS),
        "survival_probs": primary["survival_probs"],
        "decay_rate": primary.get("decay_rate_p", 0),
        "epc": primary.get("epc", 0),
        "gate_fidelity": primary.get("gate_fidelity", 0),
        "rb_model": "F(m) = A * p^m + B",
        "epc_formula": "EPC = (1-p)(d-1)/d, d=2 → EPC = (1-p)/2",
        "all_error_rates": all_rb_results,
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "rb_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nRandomized benchmarking complete.")


if __name__ == "__main__":
    main()
