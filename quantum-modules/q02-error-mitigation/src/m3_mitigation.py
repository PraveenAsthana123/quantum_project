"""
Q02 — Measurement Error Mitigation (M3 / calibration matrix approach).

Implements the calibration-matrix readout error mitigation approach:
  1. Build an 8×8 calibration matrix A where A[i][j] = P(measure i | prepare j).
  2. Simulate noisy counts by applying readout errors.
  3. Invert the calibration matrix to recover corrected counts.
  4. Compare raw vs corrected error rates.

References:
  - mthree (matrix-free measurement mitigation)
  - Qiskit Aer noise models for readout errors
  - /mnt/deepa/quantum/github/mitiq/mitiq/rem/

Saves results to data/m3_results.json.
"""

import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

RESULTS_PATH = Path(__file__).parent.parent / "data" / "m3_results.json"
RNG = np.random.default_rng(42)

N_QUBITS = 3
N_STATES = 2 ** N_QUBITS  # 8
N_SHOTS = 8192


# ── Readout error model ───────────────────────────────────────────────────

def make_readout_errors(n_qubits: int, seed: int = 0) -> np.ndarray:
    """
    Return a (n_qubits, 2, 2) array of per-qubit readout error matrices.
    E[q][i][j] = P(report i | true j)  for i,j in {0,1}.
    """
    rng = np.random.default_rng(seed)
    E = np.zeros((n_qubits, 2, 2))
    for q in range(n_qubits):
        p01 = rng.uniform(0.02, 0.08)   # P(report 1 | true 0) — assignment error
        p10 = rng.uniform(0.01, 0.05)   # P(report 0 | true 1)
        E[q] = [[1 - p01, p10],
                [p01,     1 - p10]]
    return E


def build_calibration_matrix(readout_errors: np.ndarray, n_qubits: int) -> np.ndarray:
    """
    Build 2^n × 2^n calibration matrix A where column j = P(outcome | prepare |j⟩).
    Uses tensor product of per-qubit matrices.
    """
    # Tensor product of per-qubit readout matrices
    A = readout_errors[0]
    for q in range(1, n_qubits):
        A = np.kron(A, readout_errors[q])
    return A


def apply_readout_noise(ideal_probs: np.ndarray, calib_matrix: np.ndarray) -> np.ndarray:
    """Apply calibration matrix: noisy_probs = A @ ideal_probs."""
    return calib_matrix @ ideal_probs


def sample_counts(probs: np.ndarray, n_shots: int) -> dict:
    """Sample count dictionary from a probability distribution."""
    counts = RNG.multinomial(n_shots, probs / probs.sum())
    return {format(i, f"0{N_QUBITS}b"): int(counts[i]) for i in range(len(counts)) if counts[i] > 0}


def correct_counts(raw_probs: np.ndarray, calib_matrix: np.ndarray) -> np.ndarray:
    """
    Solve A @ x = b for x (corrected probabilities) using least-squares
    constrained to non-negative values.
    """
    from scipy.optimize import nnls
    corrected, _ = nnls(calib_matrix, raw_probs)
    # Normalize
    if corrected.sum() > 0:
        corrected /= corrected.sum()
    return corrected


def tvd(p: np.ndarray, q: np.ndarray) -> float:
    """Total variation distance between two probability distributions."""
    return 0.5 * float(np.sum(np.abs(p - q)))


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Q02 — Measurement Error Mitigation (Calibration Matrix)")
    print("=" * 60)

    # Build circuit whose ideal output we want to measure
    # Use a 3-qubit GHZ state: (|000⟩ + |111⟩) / √2
    qc = QuantumCircuit(N_QUBITS)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    sv = Statevector.from_instruction(qc)
    ideal_probs = np.array(sv.probabilities())  # shape (8,)
    print(f"\n  Circuit: 3-qubit GHZ state")
    print(f"  Ideal prob distribution: {dict(zip([format(i,'03b') for i in range(8)], ideal_probs.round(4)))}")

    # Build readout error model
    readout_errors = make_readout_errors(N_QUBITS, seed=7)
    print("\n  Per-qubit readout errors:")
    for q in range(N_QUBITS):
        p01 = readout_errors[q, 1, 0]
        p10 = readout_errors[q, 0, 1]
        print(f"    Qubit {q}: P(1|0)={p01:.4f}, P(0|1)={p10:.4f}")

    # Calibration matrix
    calib_matrix = build_calibration_matrix(readout_errors, N_QUBITS)
    print(f"\n  Calibration matrix A (8×8) built ✓")
    print(f"  Condition number: {np.linalg.cond(calib_matrix):.3f}")

    # Apply noise
    noisy_probs = apply_readout_noise(ideal_probs, calib_matrix)
    noisy_counts = sample_counts(noisy_probs, N_SHOTS)
    print(f"\n  Noisy counts ({N_SHOTS} shots): {noisy_counts}")

    # Correct using calibration matrix inversion
    noisy_probs_empirical = np.zeros(N_STATES)
    for bitstr, cnt in noisy_counts.items():
        noisy_probs_empirical[int(bitstr, 2)] = cnt
    noisy_probs_empirical /= N_SHOTS

    corrected_probs = correct_counts(noisy_probs_empirical, calib_matrix)

    # Reconstruct corrected counts
    corrected_counts = {
        format(i, f"0{N_QUBITS}b"): int(round(corrected_probs[i] * N_SHOTS))
        for i in range(N_STATES)
        if corrected_probs[i] * N_SHOTS > 0.5
    }
    print(f"\n  Corrected counts: {corrected_counts}")

    # Error rates (TVD vs ideal)
    error_rate_before = tvd(noisy_probs_empirical, ideal_probs)
    error_rate_after = tvd(corrected_probs, ideal_probs)
    print(f"\n  TVD from ideal (before mitigation): {error_rate_before:.6f}")
    print(f"  TVD from ideal (after mitigation) : {error_rate_after:.6f}")
    print(f"  Error reduction: {(error_rate_before - error_rate_after)/error_rate_before*100:.1f}%")

    data = {
        "circuit": "3-qubit GHZ",
        "n_qubits": N_QUBITS,
        "n_shots": N_SHOTS,
        "calibration_matrix_shape": [N_STATES, N_STATES],
        "calibration_matrix_condition_number": round(float(np.linalg.cond(calib_matrix)), 4),
        "per_qubit_readout_errors": [
            {"qubit": q, "p_1_given_0": round(float(readout_errors[q, 1, 0]), 6),
             "p_0_given_1": round(float(readout_errors[q, 0, 1]), 6)}
            for q in range(N_QUBITS)
        ],
        "raw_counts": noisy_counts,
        "corrected_counts": corrected_counts,
        "error_rate_before": round(error_rate_before, 8),
        "error_rate_after": round(error_rate_after, 8),
        "error_reduction_pct": round((error_rate_before - error_rate_after) / max(error_rate_before, 1e-12) * 100, 3),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
