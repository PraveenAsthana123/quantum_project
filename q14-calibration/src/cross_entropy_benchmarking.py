"""
Cross-Entropy Benchmarking (XEB)
==================================
Generates random circuits of increasing depth, computes the classical XEB score,
and shows fidelity decay with circuit depth.

XEB Score:
    F_XEB = 2^n · ⟨p_ideal(x)⟩_x  −  1

where:
    n         = number of qubits
    p_ideal(x) = ideal probability of outcome x (from classical simulation)
    ⟨·⟩_x     = average over measured outcomes x

For an ideal quantum device: F_XEB → 1
For a fully depolarized device: F_XEB → 0

The fidelity per cycle: F_cycle = p^d  (p = 1 - error_per_cycle, d = depth)

Saves results to data/xeb_results.json.
"""

import json
import numpy as np
from pathlib import Path
from scipy.optimize import curve_fit


# ---------------------------------------------------------------------------
# Random circuit generation and simulation
# ---------------------------------------------------------------------------

I2  = np.eye(2, dtype=complex)
X   = np.array([[0, 1], [1, 0]], dtype=complex)
Y   = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z   = np.array([[1, 0], [0, -1]], dtype=complex)
H   = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
S   = np.array([[1, 0], [0, 1j]], dtype=complex)
T   = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
SX  = np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex) / 2  # sqrt-X

SINGLE_QUBIT_GATE_POOL = [H, S, T, SX, X, Y, Z]


def random_single_qubit_gate(rng: np.random.Generator) -> np.ndarray:
    """Sample a random single-qubit gate from the pool."""
    idx = rng.integers(0, len(SINGLE_QUBIT_GATE_POOL))
    return SINGLE_QUBIT_GATE_POOL[idx]


def random_su2(rng: np.random.Generator) -> np.ndarray:
    """Generate a Haar-random SU(2) gate."""
    z = rng.standard_normal(2) + 1j * rng.standard_normal(2)
    z /= np.linalg.norm(z)
    return np.array([[z[0], -z[1].conj()],
                     [z[1],  z[0].conj()]], dtype=complex)


def apply_gate_1q(state: np.ndarray, gate: np.ndarray,
                   qubit: int, n: int) -> np.ndarray:
    """Apply a single-qubit gate to qubit `qubit` in n-qubit state."""
    ops = [gate if q == qubit else I2 for q in range(n)]
    op = ops[0]
    for o in ops[1:]:
        op = np.kron(op, o)
    return op @ state


def apply_cnot(state: np.ndarray, control: int, target: int, n: int) -> np.ndarray:
    """Apply CNOT gate."""
    dim = 2 ** n
    new_state = np.zeros(dim, dtype=complex)
    for k in range(dim):
        bits = [(k >> (n - 1 - q)) & 1 for q in range(n)]
        if bits[control] == 1:
            bits[target] ^= 1
        new_k = sum(bits[q] << (n - 1 - q) for q in range(n))
        new_state[new_k] += state[k]
    return new_state


def random_circuit_layer(state: np.ndarray, n_qubits: int,
                          rng: np.random.Generator) -> np.ndarray:
    """
    Apply one random circuit layer:
    1. Random single-qubit gates on all qubits
    2. CNOT on pairs (0,1), (2,3), ... (entangling layer)
    """
    for q in range(n_qubits):
        gate = random_su2(rng)
        state = apply_gate_1q(state, gate, q, n_qubits)

    # Entangling gates
    for q in range(0, n_qubits - 1, 2):
        state = apply_cnot(state, control=q, target=q + 1, n=n_qubits)

    return state


def ideal_probabilities(n_qubits: int, depth: int,
                         seed: int = 42) -> np.ndarray:
    """
    Simulate ideal random circuit of given depth, return output probabilities.
    """
    rng = np.random.default_rng(seed)
    dim = 2 ** n_qubits
    state = np.zeros(dim, dtype=complex)
    state[0] = 1.0  # |000...0⟩

    for _ in range(depth):
        state = random_circuit_layer(state, n_qubits, rng)

    return np.abs(state) ** 2


def xeb_score(ideal_probs: np.ndarray, samples: list) -> float:
    """
    Compute XEB score: F_XEB = 2^n · ⟨p_ideal(x)⟩_x  − 1

    samples: list of integers (bitstring outcomes)
    """
    n = int(np.round(np.log2(len(ideal_probs))))
    if not samples:
        return 0.0
    mean_p = np.mean([ideal_probs[x] for x in samples if 0 <= x < len(ideal_probs)])
    return float((2 ** n) * mean_p - 1)


def noisy_samples(ideal_probs: np.ndarray, error_per_cycle: float,
                   depth: int, n_shots: int, rng: np.random.Generator) -> list:
    """
    Simulate noisy measurement outcomes.
    With probability p^depth, sample from ideal distribution.
    With probability 1-p^depth, sample uniformly (depolarized).
    """
    n = int(np.round(np.log2(len(ideal_probs))))
    dim = 2 ** n
    fidelity = (1 - error_per_cycle) ** depth

    samples = []
    for _ in range(n_shots):
        if rng.random() < fidelity:
            # Sample from ideal
            outcome = rng.choice(dim, p=ideal_probs)
        else:
            # Depolarized: uniform
            outcome = rng.integers(0, dim)
        samples.append(int(outcome))
    return samples


# ---------------------------------------------------------------------------
# XEB experiment
# ---------------------------------------------------------------------------

def run_xeb_experiment(n_qubits: int, depths: list,
                        error_per_cycle: float = 0.005,
                        n_circuits: int = 10, n_shots: int = 200,
                        seed: int = 42) -> dict:
    """
    Run XEB experiment over multiple depths and circuit instances.
    """
    rng = np.random.default_rng(seed)
    xeb_scores = []
    fidelity_per_cycle_list = []

    for depth in depths:
        scores_at_depth = []
        for circuit_idx in range(n_circuits):
            # Different seed per circuit
            circuit_seed = seed * 1000 + depth * 100 + circuit_idx

            # Get ideal probabilities
            ideal_p = ideal_probabilities(n_qubits, depth, seed=circuit_seed)

            # Get noisy samples
            samples = noisy_samples(ideal_p, error_per_cycle, depth, n_shots, rng)

            # Compute XEB score
            score = xeb_score(ideal_p, samples)
            scores_at_depth.append(score)

        mean_score = float(np.mean(scores_at_depth))
        xeb_scores.append(round(mean_score, 6))
        # Theoretical fidelity per cycle
        fidelity_per_cycle_list.append(round(float((1 - error_per_cycle) ** depth), 6))

    return {
        "depths": depths,
        "xeb_scores": xeb_scores,
        "fidelity_per_cycle": fidelity_per_cycle_list,
    }


def fit_xeb_decay(depths: list, xeb_scores: list) -> dict:
    """Fit exponential decay to XEB scores: F = p^d."""
    try:
        def model(d, p):
            return p ** d

        popt, pcov = curve_fit(model, depths, xeb_scores,
                                p0=[0.99], bounds=([0], [1]),
                                maxfev=2000)
        p_fit = float(popt[0])
        error_per_cycle = 1 - p_fit
        extrapolated_50 = p_fit ** 50

        return {
            "fitted_fidelity_per_cycle": round(p_fit, 8),
            "extracted_error_per_cycle": round(error_per_cycle, 8),
            "extrapolated_fidelity_d50": round(extrapolated_50, 8),
            "fit_success": True,
        }
    except Exception as e:
        return {"fit_success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Cross-Entropy Benchmarking (XEB)")
    print("=" * 60)

    n_qubits = 3
    depths = [1, 2, 4, 6, 8, 12, 16, 24, 32]
    error_per_cycle = 0.005  # 0.5% error per cycle

    print(f"\nQubits         : {n_qubits}")
    print(f"Circuit depths : {depths}")
    print(f"Error/cycle    : {error_per_cycle}")
    print(f"XEB formula    : F_XEB = 2^n · ⟨p_ideal(x)⟩ − 1\n")

    xeb_data = run_xeb_experiment(
        n_qubits=n_qubits,
        depths=depths,
        error_per_cycle=error_per_cycle,
        n_circuits=8,
        n_shots=150,
    )

    print(f"{'Depth':>8} | {'XEB Score':>12} | {'Theory F':>10}")
    print("-" * 36)
    for d, score, fpc in zip(depths, xeb_data["xeb_scores"], xeb_data["fidelity_per_cycle"]):
        print(f"{d:>8} | {score:>12.6f} | {fpc:>10.6f}")

    fit = fit_xeb_decay(depths, xeb_data["xeb_scores"])
    if fit["fit_success"]:
        print(f"\nFitted fidelity/cycle : {fit['fitted_fidelity_per_cycle']:.6f}")
        print(f"Extracted error/cycle : {fit['extracted_error_per_cycle']:.6f}")
        print(f"Extrapolated F(d=50)  : {fit['extrapolated_fidelity_d50']:.6f}")

    results = {
        "n_qubits": n_qubits,
        "depths": depths,
        "xeb_scores": xeb_data["xeb_scores"],
        "fidelity_per_cycle": xeb_data["fidelity_per_cycle"],
        "theoretical_error_per_cycle": error_per_cycle,
        **fit,
        "xeb_formula": "F_XEB = 2^n * <p_ideal(x)>_x - 1",
        "xeb_description": (
            "XEB benchmarks quantum processors by comparing the output distribution "
            "of a random circuit to its classically-computed ideal distribution. "
            "F_XEB → 1 for ideal hardware, → 0 for fully depolarized hardware."
        ),
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "xeb_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nCross-entropy benchmarking complete.")


if __name__ == "__main__":
    main()
