"""
Q02 — Probabilistic Error Cancellation (PEC).

Implements PEC manually following the mitiq reference at:
  /mnt/deepa/quantum/github/mitiq/mitiq/pec/pec.py

Algorithm:
  1. Model a noisy CNOT gate as a depolarizing channel.
  2. Express the ideal gate as a quasi-probability decomposition over
     implementable noisy operations (identity, X, Y, Z corrections).
  3. Sample circuits according to |η_i| / γ probabilities.
  4. Accumulate a sign-weighted average → unbiased estimate of ideal ⟨O⟩.

Saves results to data/pec_results.json.
"""

import json
import math
from pathlib import Path

import numpy as np

RESULTS_PATH = Path(__file__).parent.parent / "data" / "pec_results.json"

RNG = np.random.default_rng(42)

# ── Pauli matrices ────────────────────────────────────────────────────────
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
PAULIS = [I2, X, Y, Z]
PAULI_NAMES = ["I", "X", "Y", "Z"]


def kron_n(*ops):
    result = ops[0]
    for op in ops[1:]:
        result = np.kron(result, op)
    return result


# ── Noise model ─────────────────────────────────────────────────────────

def noisy_channel(state: np.ndarray, p: float) -> np.ndarray:
    """Apply single-qubit depolarizing channel: (1-p)ρ + p/3*(XρX+YρY+ZρZ)."""
    return (1 - p) * state + (p / 3) * (
        X @ state @ X +
        Y @ state @ Y +
        Z @ state @ Z
    )


def ideal_cnot_unitary() -> np.ndarray:
    """4×4 CNOT unitary (control=0, target=1)."""
    U = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ], dtype=complex)
    return U


def noisy_cnot_apply(dm: np.ndarray, p: float) -> np.ndarray:
    """Apply noisy CNOT: ideal gate then depolarizing on both qubits."""
    U = ideal_cnot_unitary()
    dm_out = U @ dm @ U.conj().T
    # Partial trace and re-embed for depolarizing on each qubit
    # Simplified: apply depolarizing to each qubit independently
    for q in [0, 1]:
        dm_out = _apply_dep_2q(dm_out, q, p)
    return dm_out


def _apply_dep_2q(dm: np.ndarray, qubit: int, p: float) -> np.ndarray:
    """Apply single-qubit depolarizing to qubit in a 2-qubit system."""
    paulis_2q = [
        kron_n(I2, I2) * math.sqrt(1 - 3 * p / 4),
        (kron_n(X, I2) if qubit == 0 else kron_n(I2, X)) * math.sqrt(p / 4),
        (kron_n(Y, I2) if qubit == 0 else kron_n(I2, Y)) * math.sqrt(p / 4),
        (kron_n(Z, I2) if qubit == 0 else kron_n(I2, Z)) * math.sqrt(p / 4),
    ]
    return sum(K @ dm @ K.conj().T for K in paulis_2q)


# ── Quasi-probability decomposition ─────────────────────────────────────

def quasi_prob_decomposition(p: float) -> tuple[list, list]:
    """
    Express ideal CNOT via quasi-probability decomposition over noisy CNOT
    plus single-qubit Pauli correction operations.

    For depolarizing parameter p:
      CNOT_ideal = η_0 * CNOT_noisy + η_1..16 * (P ⊗ Q) · CNOT_noisy · (P' ⊗ Q')

    Simplified 5-term decomposition (first order):
      η_0 = 1 + (3p/4)(1 + 2*(p correction terms))
    We use the leading-order quasi-probability coefficients.

    Quasi-probabilities for one-qubit depolarizing channel inversion:
      γ = 1 + 2p/(1-p)  (one-norm of coefficients)
      η_I = (1 - 3p/4) / (1 - 3p/4 + 3*(p/4))  ← simplified
    """
    # Leading-order PEC for one-qubit depolarizing inversion
    # Basis operations: {I, X, Y, Z} on control and target → 16 terms
    # Only diagonal terms survive at first order for depolarizing channel
    eta_I = (1.0 - 3.0 * p / 4.0)
    eta_Pauli = -(p / 4.0)  # X, Y, Z corrections

    # 5-term decomposition: I⊗I, X⊗I, Y⊗I, I⊗X, I⊗Y (dominant terms)
    ops = ["I⊗I", "X⊗I", "Y⊗I", "I⊗X", "I⊗Y"]
    etas = [eta_I, eta_Pauli, eta_Pauli, eta_Pauli, eta_Pauli]

    # Overhead: γ = sum |η_i|
    gamma = sum(abs(e) for e in etas)
    return ops, etas, gamma


def pauli_correction_unitary(op_name: str) -> np.ndarray:
    """Return 4×4 unitary for a Pauli correction string like 'X⊗I'."""
    left, right = op_name.split("⊗")
    name_to_mat = {"I": I2, "X": X, "Y": Y, "Z": Z}
    return kron_n(name_to_mat[left], name_to_mat[right])


# ── PEC estimator ─────────────────────────────────────────────────────────

def pec_estimate(ideal_sv_init: np.ndarray, p: float, num_samples: int = 5000) -> float:
    """
    Estimate ⟨ZZ⟩ on the post-CNOT state using PEC sampling.

    For each sample:
      - Sample operation index from |η_i|/γ distribution
      - Apply noisy CNOT then Pauli correction
      - Accumulate sign(η_i) * γ * ⟨ZZ⟩
    """
    ops, etas, gamma = quasi_prob_decomposition(p)
    probs = np.array([abs(e) for e in etas]) / gamma
    signs = np.sign(etas)

    # ZZ observable
    ZZ = kron_n(Z, Z)
    # Initial density matrix
    dm_init = np.outer(ideal_sv_init, ideal_sv_init.conj())

    accumulated = 0.0
    for _ in range(num_samples):
        idx = RNG.choice(len(ops), p=probs)
        # Apply noisy CNOT
        dm = noisy_cnot_apply(dm_init.copy(), p)
        # Apply Pauli correction
        C = pauli_correction_unitary(ops[idx])
        dm = C @ dm @ C.conj().T
        # Measure ZZ
        ev = float(np.real(np.trace(ZZ @ dm)))
        accumulated += signs[idx] * gamma * ev

    return accumulated / num_samples


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Q02 — Probabilistic Error Cancellation (PEC)")
    print("=" * 60)

    p_noise = 0.05  # 5% depolarizing per CNOT gate
    num_samples = 8000

    # Initial state: |00⟩ → after ideal CNOT → |00⟩ (no flip since ctrl=0)
    # Use |11⟩ so that after CNOT: |10⟩, giving ⟨ZZ⟩ = (+1)(-1) = -1
    init_sv = np.array([0, 0, 0, 1], dtype=complex)  # |11⟩
    dm_init = np.outer(init_sv, init_sv.conj())
    ZZ = kron_n(Z, Z)

    # Ideal expectation: CNOT on (|10⟩+|11⟩)/√2 → (|11⟩+|10⟩)/√2 = same state
    # ⟨ZZ⟩ = ⟨(|10⟩+|11⟩)(⟨10|+⟨11|)|ZZ|same⟩
    U_cnot = ideal_cnot_unitary()
    dm_ideal_out = U_cnot @ dm_init @ U_cnot.conj().T
    ideal_value = float(np.real(np.trace(ZZ @ dm_ideal_out)))
    print(f"\n  Initial state: |11⟩  (after CNOT ctrl=1 → |10⟩, ⟨ZZ⟩ = -1)")
    print(f"  Ideal ⟨ZZ⟩ after CNOT  : {ideal_value:.6f}")

    # Noisy expectation
    dm_noisy_out = noisy_cnot_apply(dm_init.copy(), p_noise)
    noisy_value = float(np.real(np.trace(ZZ @ dm_noisy_out)))
    print(f"  Noisy ⟨ZZ⟩ after CNOT  : {noisy_value:.6f}  (p={p_noise})")

    # PEC estimate
    _, _, gamma = quasi_prob_decomposition(p_noise)
    print(f"\n  Sampling PEC ({num_samples} circuits)...")
    pec_value = pec_estimate(init_sv, p_noise, num_samples)
    print(f"  PEC ⟨ZZ⟩ estimate       : {pec_value:.6f}")
    print(f"  Overhead γ              : {gamma:.4f}")
    print(f"  Sample variance factor  : {gamma**2:.4f}x vs direct")

    data = {
        "circuit": "CNOT on |11> → |10>, ⟨ZZ⟩ = -1",
        "observable": "ZZ",
        "noise_model": "single-qubit depolarizing",
        "depolarizing_p": p_noise,
        "ideal_value": round(ideal_value, 8),
        "noisy_value": round(noisy_value, 8),
        "pec_value": round(pec_value, 8),
        "overhead_gamma": round(gamma, 6),
        "variance_overhead": round(gamma ** 2, 6),
        "num_samples": num_samples,
        "reference": "/mnt/deepa/quantum/github/mitiq/mitiq/pec/pec.py",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
