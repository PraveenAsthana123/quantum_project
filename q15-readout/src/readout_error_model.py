"""
Readout Error Model — 3-Qubit Confusion Matrix
================================================
Models readout errors using a confusion matrix and applies readout error
mitigation to a 3-qubit GHZ state measurement.

Confusion matrix A[i,j] = P(report i | prepared j):
  - P(0|1) = 0.03  (miss: prepared |1⟩, measured as |0⟩)
  - P(1|0) = 0.01  (false trigger: prepared |0⟩, measured as |1⟩)

For 3 qubits: A_3q = A₁ ⊗ A₂ ⊗ A₃  (tensor product)

Mitigation: apply A^{-1} to the measured counts vector.

Saves results to data/readout_model_results.json.
"""

import json
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Single-qubit readout confusion matrix
# ---------------------------------------------------------------------------

def qubit_confusion_matrix(p01: float, p10: float) -> np.ndarray:
    """
    Single-qubit confusion matrix.
    A[reported, prepared]:
      A[0,0] = P(0|0) = 1 - p10
      A[1,0] = P(1|0) = p10
      A[0,1] = P(0|1) = p01
      A[1,1] = P(1|1) = 1 - p01
    """
    return np.array([
        [1 - p10,      p01],
        [p10,      1 - p01],
    ], dtype=float)


def n_qubit_confusion_matrix(p01: float, p10: float, n_qubits: int) -> np.ndarray:
    """
    n-qubit confusion matrix as tensor product of single-qubit matrices.
    Shape: (2^n, 2^n)
    """
    A1 = qubit_confusion_matrix(p01, p10)
    A = A1
    for _ in range(n_qubits - 1):
        A = np.kron(A, A1)
    return A


# ---------------------------------------------------------------------------
# GHZ state generation
# ---------------------------------------------------------------------------

def ghz_state_probabilities(n_qubits: int) -> np.ndarray:
    """
    Ideal GHZ state: |GHZ⟩ = (|00...0⟩ + |11...1⟩) / √2
    Measurement probabilities: P(00...0) = P(11...1) = 0.5, all others = 0.
    """
    dim = 2 ** n_qubits
    probs = np.zeros(dim)
    probs[0] = 0.5              # |000...0⟩
    probs[dim - 1] = 0.5        # |111...1⟩
    return probs


def simulate_measurement_counts(probs: np.ndarray, n_shots: int = 10000,
                                  seed: int = 42) -> np.ndarray:
    """Sample measurement outcomes from a probability distribution."""
    rng = np.random.default_rng(seed)
    dim = len(probs)
    counts = rng.multinomial(n_shots, probs)
    return counts.astype(float)


def apply_confusion_matrix(ideal_counts: np.ndarray,
                             A: np.ndarray) -> np.ndarray:
    """
    Apply confusion matrix to ideal counts to simulate readout errors.
    noisy_counts = A · ideal_counts
    """
    return A @ ideal_counts


def readout_error_mitigation(noisy_counts: np.ndarray,
                               A: np.ndarray) -> np.ndarray:
    """
    Apply readout error mitigation via matrix inversion:
    corrected_counts = A^{-1} · noisy_counts

    Clip negative values (physical constraint).
    """
    A_inv = np.linalg.inv(A)
    corrected = A_inv @ noisy_counts
    # Enforce non-negative counts (MLE projection)
    corrected = np.maximum(corrected, 0)
    return corrected


# ---------------------------------------------------------------------------
# Fidelity metrics
# ---------------------------------------------------------------------------

def fidelity_to_ghz(counts: np.ndarray, n_qubits: int) -> float:
    """
    Fidelity of measured distribution to ideal GHZ distribution.
    F = Σ_x √(P_ideal(x) · P_measured(x))   [Bhattacharyya coefficient]
    Simplified: F = (counts[0] + counts[-1]) / sum(counts) for GHZ
    """
    total = np.sum(counts)
    if total < 1e-10:
        return 0.0
    dim = 2 ** n_qubits
    # GHZ fidelity: fraction of |000⟩ and |111⟩ outcomes
    ghz_counts = counts[0] + counts[dim - 1]
    return float(ghz_counts / total)


def state_fidelity_to_ghz(counts: np.ndarray, n_qubits: int) -> float:
    """
    State fidelity: requires off-diagonal measurement too.
    Here we use the diagonal fidelity as an approximation.
    """
    return fidelity_to_ghz(counts, n_qubits)


# ---------------------------------------------------------------------------
# Error analysis
# ---------------------------------------------------------------------------

def analyze_error_rates(A: np.ndarray, n_qubits: int) -> dict:
    """Compute aggregate error statistics."""
    dim = 2 ** n_qubits
    # Average probability of error for each prepared state
    error_rates = []
    for j in range(dim):
        # Probability of measuring incorrectly
        p_error = 1.0 - A[j, j]
        error_rates.append(float(p_error))

    return {
        "mean_error_rate": round(float(np.mean(error_rates)), 6),
        "max_error_rate": round(float(np.max(error_rates)), 6),
        "min_error_rate": round(float(np.min(error_rates)), 6),
        "error_rates_by_state": [round(e, 6) for e in error_rates[:8]],  # first 8
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Readout Error Model — 3-Qubit GHZ State")
    print("=" * 60)

    n_qubits = 3
    p01 = 0.03   # P(0|1): miss probability
    p10 = 0.01   # P(1|0): false trigger probability
    n_shots = 10000

    print(f"\nQubits        : {n_qubits}")
    print(f"P(0|1)        : {p01}  (miss)")
    print(f"P(1|0)        : {p10}  (false trigger)")
    print(f"Shots         : {n_shots}")

    # Single-qubit confusion matrix
    A1 = qubit_confusion_matrix(p01, p10)
    print(f"\nSingle-qubit confusion matrix:")
    print(f"  [[{A1[0,0]:.4f}, {A1[0,1]:.4f}],")
    print(f"   [{A1[1,0]:.4f}, {A1[1,1]:.4f}]]")

    # 3-qubit confusion matrix
    A3 = n_qubit_confusion_matrix(p01, p10, n_qubits)
    print(f"\n3-qubit confusion matrix shape: {A3.shape}")
    print(f"  Condition number: {np.linalg.cond(A3):.4f}")
    print(f"  Determinant: {np.linalg.det(A3):.6f}")

    # GHZ state ideal probabilities
    ideal_probs = ghz_state_probabilities(n_qubits)
    ideal_counts = ideal_probs * n_shots

    # Apply readout errors
    noisy_counts = apply_confusion_matrix(ideal_counts, A3)
    noisy_probs = noisy_counts / n_shots

    # Readout error mitigation
    corrected_counts = readout_error_mitigation(noisy_counts, A3)
    corrected_probs = corrected_counts / max(np.sum(corrected_counts), 1)

    # Fidelities
    fid_ideal = fidelity_to_ghz(ideal_counts, n_qubits)
    fid_noisy = fidelity_to_ghz(noisy_counts, n_qubits)
    fid_corrected = fidelity_to_ghz(corrected_counts, n_qubits)

    print(f"\n{'State':>8} | {'Ideal':>10} | {'Noisy':>10} | {'Corrected':>12}")
    print("-" * 48)
    dim = 2 ** n_qubits
    state_labels = [bin(k)[2:].zfill(n_qubits) for k in range(dim)]
    for k in range(dim):
        ideal_f = ideal_probs[k]
        noisy_f = noisy_probs[k]
        corr_f = float(corrected_probs[k])
        if ideal_f > 0.01 or noisy_f > 0.01:
            print(f"{state_labels[k]:>8} | {ideal_f:>10.4f} | {noisy_f:>10.4f} | {corr_f:>12.4f}")

    print(f"\nGHZ fidelity (ideal)    : {fid_ideal:.6f}")
    print(f"GHZ fidelity (noisy)    : {fid_noisy:.6f}")
    print(f"GHZ fidelity (corrected): {fid_corrected:.6f}")

    # Confusion matrix (formatted)
    A3_formatted = A3.tolist()
    error_analysis = analyze_error_rates(A3, n_qubits)

    results = {
        "n_qubits": n_qubits,
        "confusion_matrix": {
            "p01": p01,
            "p10": p10,
            "single_qubit": A1.tolist(),
            "n_qubit_shape": list(A3.shape),
            "condition_number": round(float(np.linalg.cond(A3)), 4),
        },
        "error_rates": {
            "p01": p01,
            "p10": p10,
            **error_analysis,
        },
        "ghz_state": {
            "ideal_probs": ideal_probs.tolist(),
            "noisy_probs": [round(p, 6) for p in noisy_probs.tolist()],
            "corrected_probs": [round(p, 6) for p in corrected_probs.tolist()],
        },
        "fidelity_ideal": round(fid_ideal, 6),
        "fidelity_noisy": round(fid_noisy, 6),
        "corrected_fidelity": round(fid_corrected, 6),
        "fidelity_improvement": round(fid_corrected - fid_noisy, 6),
        "n_shots": n_shots,
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "readout_model_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nReadout error model simulation complete.")


if __name__ == "__main__":
    main()
