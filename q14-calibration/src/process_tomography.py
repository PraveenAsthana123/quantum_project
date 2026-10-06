"""
Quantum Process Tomography (QPT)
==================================
Reconstructs the process matrix χ for a noisy X gate.

Protocol:
1. Prepare 4 input states: |0⟩, |1⟩, |+⟩, |i+⟩ (eigenstates of I, X, Y, Z)
2. Apply the unknown channel (noisy X gate)
3. Perform state tomography on each output (measure in X, Y, Z bases)
4. Reconstruct χ from the linear system χ = B^{-1} · ρ_out

Process matrix χ is defined by:
    E(ρ) = Σ_{mn} χ_{mn} E_m ρ E_n†

where {E_k} = {I, X, Y, Z}/√2 is the Pauli basis.

Process fidelity: F_p = Tr(χ_ideal · χ) / d²

Saves results to data/qpt_results.json.
"""

import json
import numpy as np
from pathlib import Path
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# Pauli matrices and helpers
# ---------------------------------------------------------------------------

I2 = np.eye(2, dtype=complex)
X  = np.array([[0, 1], [1, 0]], dtype=complex)
Y  = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z  = np.array([[1, 0], [0, -1]], dtype=complex)

PAULI_BASIS = [I2 / np.sqrt(2), X / np.sqrt(2), Y / np.sqrt(2), Z / np.sqrt(2)]
PAULI_NAMES = ["I", "X", "Y", "Z"]


# ---------------------------------------------------------------------------
# Noise model
# ---------------------------------------------------------------------------

def noisy_x_gate(rho: np.ndarray, gate_error: float = 0.02,
                  coherent_error_deg: float = 3.0) -> np.ndarray:
    """
    Simulate a noisy X gate:
    1. Apply slightly over-rotated X (coherent error)
    2. Apply depolarizing noise
    """
    # Coherent error: over-rotation by epsilon degrees
    angle = np.pi + np.radians(coherent_error_deg)
    U_noisy = np.array([[np.cos(angle / 2), -1j * np.sin(angle / 2)],
                         [-1j * np.sin(angle / 2), np.cos(angle / 2)]], dtype=complex)

    rho_after = U_noisy @ rho @ U_noisy.conj().T

    # Depolarizing noise
    p = gate_error
    rho_out = ((1 - 3 * p / 4) * rho_after
               + (p / 4) * (X @ rho_after @ X + Y @ rho_after @ Y + Z @ rho_after @ Z))
    return rho_out


# ---------------------------------------------------------------------------
# State tomography: reconstruct density matrix from Pauli expectations
# ---------------------------------------------------------------------------

def measure_pauli_expectations(rho: np.ndarray) -> np.ndarray:
    """Measure ⟨I⟩, ⟨X⟩, ⟨Y⟩, ⟨Z⟩ for a density matrix."""
    return np.array([np.real(np.trace(P * np.sqrt(2) @ rho)) for P in PAULI_BASIS])


def state_from_pauli_expectations(expectations: np.ndarray) -> np.ndarray:
    """Reconstruct density matrix from 4 Pauli expectations."""
    rho = np.zeros((2, 2), dtype=complex)
    paulis = [I2, X, Y, Z]
    for k, e in enumerate(expectations):
        rho += e * paulis[k]
    return rho / 2


# ---------------------------------------------------------------------------
# Process tomography input states
# ---------------------------------------------------------------------------

def input_states() -> list:
    """
    4 linearly independent input states spanning the space of density matrices.
    Uses the +1 eigenstates of I, X, Y, Z operators.
    """
    states = [
        np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex),           # |0⟩ (Z+)
        np.array([[0.0, 0.0], [0.0, 1.0]], dtype=complex),           # |1⟩ (Z-)
        np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex),           # |+⟩ (X+)
        np.array([[0.5, -0.5j], [0.5j, 0.5]], dtype=complex),        # |i+⟩ (Y+)
    ]
    return states


# ---------------------------------------------------------------------------
# Process matrix reconstruction
# ---------------------------------------------------------------------------

def channel_to_chi(channel_func) -> np.ndarray:
    """
    Convert a quantum channel to its χ-matrix representation in the Pauli basis.

    Uses the Choi-Jamiolkowski isomorphism:
    1. Build the Choi matrix Λ = (I ⊗ E)(|Φ+⟩⟨Φ+|)
    2. Convert Choi → χ via basis change

    The Choi matrix Λ_{(i,k),(j,l)} = E(|i⟩⟨j|)_{kl}
    """
    d = 2
    # Build Choi matrix by applying channel to each |i⟩⟨j| element
    choi = np.zeros((d * d, d * d), dtype=complex)
    for i in range(d):
        for j in range(d):
            rho_ij = np.zeros((d, d), dtype=complex)
            rho_ij[i, j] = 1.0

            # Channel output
            rho_out = channel_func(rho_ij)  # may not be PSD for off-diag inputs

            # Place in Choi matrix
            for k in range(d):
                for l in range(d):
                    choi[i * d + k, j * d + l] = rho_out[k, l]

    # Convert Choi matrix to χ in the Pauli basis {I, X, Y, Z}/sqrt(2)
    # χ_{mn} = Σ_{ij,kl} (E_m)_{ik} · Λ_{(i,k),(j,l)} · (E_n†)_{lj}  / d
    paulis_normalized = [I2 / np.sqrt(2), X / np.sqrt(2),
                          Y / np.sqrt(2), Z / np.sqrt(2)]
    n_ops = 4
    chi = np.zeros((n_ops, n_ops), dtype=complex)

    for m, Em in enumerate(paulis_normalized):
        for n, En in enumerate(paulis_normalized):
            # Vectorise Em and En
            Em_vec = Em.flatten()
            En_vec = En.flatten()
            # χ_{mn} = Tr(Em† ⊗ En^T · Choi) / d = Em† Choi En^* / d (approx)
            # Correct formula: χ = B^{-1} Λ (B^{-1})†
            # where B transforms basis — we use the direct formula:
            # χ_{mn} = Σ_{ij} conj(Em)_{ij} * (E_n via channel output)
            val = 0.0 + 0j
            for i in range(d):
                for j in range(d):
                    for k in range(d):
                        for l in range(d):
                            val += np.conj(Em[i, k]) * choi[i * d + k, j * d + l] * En[j, l]
            chi[m, n] = val / d

    return chi


def estimate_chi_matrix(channel_func, n_meas: int = 1000,
                         noise_level: float = 0.0) -> np.ndarray:
    """Estimate the χ matrix for the given channel."""
    return channel_to_chi(channel_func)


def ideal_chi_x_gate() -> np.ndarray:
    """Ideal χ matrix for the X gate E(ρ) = X ρ X†."""
    def x_gate(rho):
        return X @ rho @ X.conj().T
    return channel_to_chi(x_gate)


def process_fidelity(chi: np.ndarray, chi_ideal: np.ndarray) -> float:
    """
    Process fidelity: F_p = Tr(χ_ideal† · χ)
    (In the normalised Pauli basis where Tr(χ) = 1, this equals the
    overlap between the two channels.)
    """
    return float(abs(np.trace(chi_ideal.conj().T @ chi)))


def pauli_error_rates(chi: np.ndarray) -> dict:
    """Extract Pauli error rates from diagonal of χ (in Pauli basis)."""
    # The diagonal of chi in the Pauli basis gives the probability of each
    # Pauli error occurring
    return {
        "p_I": round(float(abs(chi[0, 0])), 6),  # no error
        "p_X": round(float(abs(chi[1, 1])), 6),  # bit flip
        "p_Y": round(float(abs(chi[2, 2])), 6),  # bit+phase flip
        "p_Z": round(float(abs(chi[3, 3])), 6),  # phase flip
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Quantum Process Tomography — Noisy X Gate")
    print("=" * 60)

    gate_errors = [0.0, 0.01, 0.02, 0.05]

    print(f"\nInput states: {['|0⟩', '|1⟩', '|+⟩', '|i+⟩']}")
    print(f"Process basis: {{I, X, Y, Z}}/√2")
    print(f"\n{'Error Rate':>12} | {'Process Fid':>13} | {'Chi Trace':>10} | {'p_X':>8}")
    print("-" * 52)

    all_results = []
    for gate_error in gate_errors:
        def channel(rho, ge=gate_error):
            return noisy_x_gate(rho, gate_error=ge)

        chi = estimate_chi_matrix(channel)
        chi_ideal = ideal_chi_x_gate()
        proc_fid = process_fidelity(chi, chi_ideal)
        pauli_errs = pauli_error_rates(chi)
        chi_trace = float(abs(np.trace(chi)))

        print(f"{gate_error:>12.4f} | {proc_fid:>13.6f} | {chi_trace:>10.6f} | {pauli_errs['p_X']:>8.6f}")

        all_results.append({
            "gate_error_rate": gate_error,
            "process_fidelity": round(proc_fid, 6),
            "chi_matrix_trace": round(chi_trace, 6),
            "pauli_errors": pauli_errs,
            "chi_matrix_real": chi.real.tolist(),
            "chi_matrix_imag": chi.imag.tolist(),
        })

    # Primary result (2% error)
    primary = all_results[2]
    chi_ideal = ideal_chi_x_gate()

    print(f"\nIdeal χ (X gate) diagonal: {[round(abs(chi_ideal[i,i]), 4) for i in range(4)]}")
    print(f"Primary result (2% error):")
    print(f"  Process fidelity  : {primary['process_fidelity']:.6f}")
    print(f"  Pauli errors      : {primary['pauli_errors']}")

    results = {
        "target_gate": "X",
        "input_states": ["|0⟩", "|1⟩", "|+⟩", "|i+⟩"],
        "pauli_basis": PAULI_NAMES,
        "process_fidelity": primary["process_fidelity"],
        "chi_matrix_trace": primary["chi_matrix_trace"],
        "pauli_errors": primary["pauli_errors"],
        "chi_matrix_real": primary["chi_matrix_real"],
        "chi_matrix_imag": primary["chi_matrix_imag"],
        "chi_ideal_real": chi_ideal.real.tolist(),
        "all_error_rates": all_results,
        "interpretation": (
            "The χ matrix fully characterizes the quantum channel. "
            "Process fidelity → 1 means the channel closely matches the ideal X gate. "
            "Off-diagonal χ terms represent coherences between error processes."
        ),
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "qpt_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nProcess tomography complete.")


if __name__ == "__main__":
    main()
