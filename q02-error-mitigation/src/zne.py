"""
Q02 — Zero Noise Extrapolation (ZNE).

Implements ZNE manually (the mitiq package on this system is a stub).
Algorithm follows the mitiq reference at:
  /mnt/deepa/quantum/github/mitiq/mitiq/zne/zne.py

Steps:
  1. Build a 4-qubit GHZ circuit.
  2. Simulate at noise scale factors [1, 2, 3] by inserting CNOT pairs (gate
     folding: each gate is replaced by G · G† · G to double the error).
  3. Measure ⟨ZZZZ⟩ at each scale factor.
  4. Apply Richardson extrapolation to estimate the zero-noise value.
  5. Compare: ideal | noisy | ZNE-mitigated.

Saves results to data/zne_results.json.
"""

import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp

RESULTS_PATH = Path(__file__).parent.parent / "data" / "zne_results.json"

# ── Depolarizing noise model (manual density-matrix simulation) ───────────

def apply_depolarizing(dm: np.ndarray, qubit: int, n_qubits: int, p: float) -> np.ndarray:
    """Apply single-qubit depolarizing channel to density matrix."""
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)

    def embed(op, target, n):
        ops = [I] * n
        ops[target] = op
        result = ops[0]
        for o in ops[1:]:
            result = np.kron(result, o)
        return result

    E_I = embed(I, qubit, n_qubits) * math.sqrt(1 - 3 * p / 4)
    E_X = embed(X, qubit, n_qubits) * math.sqrt(p / 4)
    E_Y = embed(Y, qubit, n_qubits) * math.sqrt(p / 4)
    E_Z = embed(Z, qubit, n_qubits) * math.sqrt(p / 4)

    return (E_I @ dm @ E_I.conj().T +
            E_X @ dm @ E_X.conj().T +
            E_Y @ dm @ E_Y.conj().T +
            E_Z @ dm @ E_Z.conj().T)


def statevec_to_dm(sv: np.ndarray) -> np.ndarray:
    sv = sv.reshape(-1)
    return np.outer(sv, sv.conj())


# ── GHZ circuit builder ───────────────────────────────────────────────────

def ghz_statevector(n_qubits: int = 4) -> np.ndarray:
    """Return the ideal GHZ statevector |0000⟩ + |1111⟩ / sqrt(2)."""
    sv = np.zeros(2 ** n_qubits, dtype=complex)
    sv[0] = 1.0 / math.sqrt(2)
    sv[-1] = 1.0 / math.sqrt(2)
    return sv


def zzzz_observable(n_qubits: int) -> np.ndarray:
    """Full ZZZZ observable as a 2^n × 2^n diagonal matrix."""
    Z = np.array([1.0, -1.0])
    obs = Z.copy()
    for _ in range(n_qubits - 1):
        obs = np.kron(obs, Z)
    return np.diag(obs)


def expval_from_dm(dm: np.ndarray, obs: np.ndarray) -> float:
    return float(np.real(np.trace(obs @ dm)))


# ── Noise scaling via gate folding ─────────────────────────────────────────
# Gate folding multiplies each gate's noise by scale_factor.
# For a depolarizing channel with error p per CNOT gate on GHZ:
#   effective_p_scaled = scale_factor * base_p
# We simulate this analytically.

def simulate_ghz_with_noise(n_qubits: int, base_p_per_cnot: float, scale_factor: float) -> float:
    """
    Analytically simulate ⟨ZZZZ⟩ for a GHZ circuit at a given noise scale.

    GHZ circuit: H on qubit 0, then CNOT(0→1), CNOT(1→2), CNOT(2→3).
    Each CNOT introduces depolarizing noise on both qubits at rate
      p_eff = base_p_per_cnot * scale_factor.
    Returns ⟨ZZZZ⟩.
    """
    p_eff = min(base_p_per_cnot * scale_factor, 0.75)  # cap at max depolarizing

    # Start from ideal GHZ density matrix
    dm = statevec_to_dm(ghz_statevector(n_qubits))

    # Apply depolarizing noise for each CNOT in the circuit (3 CNOTs for 4 qubits)
    for cnot_qubit_pair in [(0, 1), (1, 2), (2, 3)]:
        for q in cnot_qubit_pair:
            dm = apply_depolarizing(dm, q, n_qubits, p_eff)

    obs = zzzz_observable(n_qubits)
    return expval_from_dm(dm, obs)


# ── Richardson extrapolation ───────────────────────────────────────────────

def richardson_extrapolation(scale_factors: list, expectation_values: list) -> float:
    """
    Richardson extrapolation to estimate zero-noise value.
    Fits a polynomial and evaluates at scale_factor = 0.

    For scale factors [1, 2, 3] and values [E1, E2, E3]:
      E(λ) ≈ a0 + a1*λ + a2*λ²
      E(0) = a0
    """
    lambdas = np.array(scale_factors, dtype=float)
    values = np.array(expectation_values, dtype=float)
    # Vandermonde matrix
    V = np.vander(lambdas, increasing=True)
    coeffs = np.linalg.lstsq(V, values, rcond=None)[0]
    return float(coeffs[0])  # constant term = value at λ=0


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Q02 — Zero Noise Extrapolation (ZNE)")
    print("=" * 60)

    n_qubits = 4
    base_p = 0.02         # 2% depolarizing error per CNOT
    scale_factors = [1, 2, 3]

    # Ideal value: ⟨ZZZZ⟩ on |GHZ⟩ = 1.0 (both |0000⟩ and |1111⟩ give +1)
    ideal_sv = ghz_statevector(n_qubits)
    obs = zzzz_observable(n_qubits)
    ideal_dm = statevec_to_dm(ideal_sv)
    ideal_value = expval_from_dm(ideal_dm, obs)
    print(f"\n  Ideal ⟨ZZZZ⟩           : {ideal_value:.6f}")

    # Noisy values at each scale factor
    expvals = []
    for sf in scale_factors:
        ev = simulate_ghz_with_noise(n_qubits, base_p, sf)
        expvals.append(ev)
        print(f"  Scale {sf}× noisy ⟨ZZZZ⟩  : {ev:.6f}")

    noisy_value = expvals[0]  # scale factor 1 = baseline noisy

    # ZNE via Richardson extrapolation
    zne_value = richardson_extrapolation(scale_factors, expvals)
    print(f"\n  ZNE (Richardson) ⟨ZZZZ⟩: {zne_value:.6f}")

    # Improvement
    noisy_error = abs(ideal_value - noisy_value)
    zne_error = abs(ideal_value - zne_value)
    improvement_pct = (noisy_error - zne_error) / noisy_error * 100 if noisy_error > 0 else 0.0
    print(f"\n  Noisy error             : {noisy_error:.6f}")
    print(f"  ZNE error               : {zne_error:.6f}")
    print(f"  Error reduction         : {improvement_pct:.1f}%")

    data = {
        "circuit": "4-qubit GHZ",
        "observable": "ZZZZ",
        "base_depolarizing_p": base_p,
        "ideal_value": round(ideal_value, 8),
        "noisy_value": round(noisy_value, 8),
        "zne_value": round(zne_value, 8),
        "scale_factors": scale_factors,
        "expvals_at_scales": [round(e, 8) for e in expvals],
        "improvement_pct": round(improvement_pct, 3),
        "noisy_error": round(noisy_error, 8),
        "zne_error": round(zne_error, 8),
        "extrapolation_method": "Richardson",
        "reference": "/mnt/deepa/quantum/github/mitiq/mitiq/zne/zne.py",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
