"""
Excited State Calculation using Variational Quantum Deflation (VQD)
Computes H2 ground state AND first excited state, with excitation energy.
"""
import numpy as np
import json
import os
from typing import Dict, List, Tuple


# Reuse H2 BK Hamiltonian from h2_vqe
H2_BK_COEFFICIENTS_074A = {
    "I":   -0.81054,
    "Z0":  +0.17218,
    "Z1":  -0.22575,
    "Z0Z1": +0.12091,
    "X0X1": -0.04523,
    "Y0Y1": -0.04523,
}

SPEED_OF_LIGHT_CM_S = 2.99792458e10  # cm/s
HARTREE_TO_EV = 27.2114
HARTREE_TO_CM_INV = 219474.63  # wavenumbers per Hartree
H_PLANCK_EV_S = 4.135667696e-15  # eV·s


def build_h2_hamiltonian() -> np.ndarray:
    """Build 4×4 H2 BK Hamiltonian at 0.74 Å."""
    I2 = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)

    c = H2_BK_COEFFICIENTS_074A
    return (c["I"] * np.kron(I2, I2)
            + c["Z0"] * np.kron(Z, I2)
            + c["Z1"] * np.kron(I2, Z)
            + c["Z0Z1"] * np.kron(Z, Z)
            + c["X0X1"] * np.kron(X, X)
            + c["Y0Y1"] * np.kron(Y, Y))


def ry_ansatz_2qubit(params: np.ndarray) -> np.ndarray:
    """4-parameter RY ansatz for 2-qubit system."""
    def ry(theta):
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        return np.array([[c, -s], [s, c]], dtype=complex)

    CNOT = np.array([[1, 0, 0, 0],
                     [0, 1, 0, 0],
                     [0, 0, 0, 1],
                     [0, 0, 1, 0]], dtype=complex)

    state = np.array([1, 0, 0, 0], dtype=complex)
    U1 = np.kron(ry(params[2]), ry(params[3]))
    state = U1 @ state
    state = CNOT @ state
    U2 = np.kron(ry(params[0]), ry(params[1]))
    state = U2 @ state
    return state


def vqe_ground_state(H: np.ndarray, seed: int = 0) -> Tuple[float, np.ndarray]:
    """Run VQE to find ground state energy and optimal parameters."""
    rng = np.random.default_rng(seed)
    best_e = np.inf
    best_p = None

    for trial in range(8):
        x = rng.uniform(-np.pi, np.pi, 4)
        step = 0.15

        def energy(p):
            s = ry_ansatz_2qubit(p)
            return float(np.real(s.conj() @ H @ s))

        e = energy(x)
        for _ in range(500):
            improved = False
            for i in range(4):
                for d in [step, -step]:
                    xn = x.copy()
                    xn[i] += d
                    en = energy(xn)
                    if en < e - 1e-10:
                        x, e = xn, en
                        improved = True
            step *= 0.995
            if not improved and step < 1e-8:
                break

        if e < best_e:
            best_e = e
            best_p = x.copy()

    return best_e, best_p


def vqd_excited_state(
    H: np.ndarray,
    ground_params: np.ndarray,
    beta: float = 2.0,
    seed: int = 1,
) -> Tuple[float, np.ndarray]:
    """
    VQD (Variational Quantum Deflation) for first excited state.
    Minimize: F(θ) = ⟨ψ(θ)|H|ψ(θ)⟩ + β·|⟨ψ(θ)|ψ₀⟩|²
    The penalty β·|overlap|² pushes the optimizer away from the ground state.
    """
    ground_state = ry_ansatz_2qubit(ground_params)
    rng = np.random.default_rng(seed)

    def penalized_energy(p):
        state = ry_ansatz_2qubit(p)
        hamiltonian_exp = float(np.real(state.conj() @ H @ state))
        overlap = abs(float(ground_state.conj() @ state)) ** 2
        return hamiltonian_exp + beta * overlap

    best_e_aug = np.inf
    best_p = None

    for trial in range(10):
        x = rng.uniform(-np.pi, np.pi, 4)
        step = 0.15
        e = penalized_energy(x)

        for _ in range(600):
            improved = False
            for i in range(4):
                for d in [step, -step]:
                    xn = x.copy()
                    xn[i] += d
                    en = penalized_energy(xn)
                    if en < e - 1e-10:
                        x, e = xn, en
                        improved = True
            step *= 0.995
            if not improved and step < 1e-8:
                break

        if e < best_e_aug:
            best_e_aug = e
            best_p = x.copy()

    # Extract actual Hamiltonian expectation (without penalty)
    excited_state = ry_ansatz_2qubit(best_p)
    excited_energy = float(np.real(excited_state.conj() @ H @ excited_state))
    return excited_energy, best_p


def excitation_wavelength(energy_diff_eV: float) -> float:
    """Convert excitation energy (eV) to photon wavelength (nm)."""
    if energy_diff_eV <= 0:
        return np.inf
    energy_J = energy_diff_eV * 1.602176634e-19
    h = 6.62607015e-34
    c = 2.99792458e8
    wavelength_m = h * c / energy_J
    return round(wavelength_m * 1e9, 2)  # nm


def get_exact_states(H: np.ndarray) -> Tuple[float, float]:
    """Exact diagonalization for reference."""
    eigenvalues = np.linalg.eigvalsh(H)
    return float(eigenvalues[0]), float(eigenvalues[1])


def main():
    print("=" * 60)
    print("H2 Excited State Calculation (VQD)")
    print("=" * 60)

    H = build_h2_hamiltonian()

    # Exact reference
    exact_gs, exact_ex = get_exact_states(H)
    exact_gap = exact_ex - exact_gs
    print(f"\n[Reference] Exact diagonalization:")
    print(f"  Ground state E0 = {exact_gs:.8f} Ha")
    print(f"  Excited state E1 = {exact_ex:.8f} Ha")
    print(f"  Excitation gap   = {exact_gap:.8f} Ha = {exact_gap*HARTREE_TO_EV:.4f} eV")

    # VQE ground state
    print("\n[1] VQE Ground State")
    vqe_gs, ground_params = vqe_ground_state(H)
    print(f"  VQE E0 = {vqe_gs:.8f} Ha  (exact: {exact_gs:.8f} Ha)")
    print(f"  Error  = {abs(vqe_gs - exact_gs)*1000:.4f} mHa")

    # VQD excited state
    print("\n[2] VQD First Excited State (β = 2.0)")
    vqd_ex, excited_params = vqd_excited_state(H, ground_params, beta=2.0)
    print(f"  VQD E1 = {vqd_ex:.8f} Ha  (exact: {exact_ex:.8f} Ha)")
    print(f"  Error  = {abs(vqd_ex - exact_ex)*1000:.4f} mHa")

    # Excitation energy
    vqd_gap = vqd_ex - vqe_gs
    vqd_gap_eV = vqd_gap * HARTREE_TO_EV
    wavelength_nm = excitation_wavelength(vqd_gap_eV)

    print(f"\n[3] Excitation Energy")
    print(f"  VQD excitation energy: {vqd_gap:.8f} Ha")
    print(f"                         {vqd_gap_eV:.4f} eV")
    print(f"                         {wavelength_nm:.2f} nm (photon wavelength)")
    print(f"  Exact excitation     : {exact_gap*HARTREE_TO_EV:.4f} eV")
    print(f"  VQD error            : {abs(vqd_gap - exact_gap)*1000:.4f} mHa")

    # Overlap check (should be near zero for orthogonal states)
    gs_state = ry_ansatz_2qubit(ground_params)
    ex_state = ry_ansatz_2qubit(excited_params)
    overlap = abs(float(gs_state.conj() @ ex_state))
    print(f"\n  Ground/excited overlap: {overlap:.6f} (ideal: 0.0)")

    output = {
        "ground_state_energy": round(vqe_gs, 8),
        "excited_state_energy": round(vqd_ex, 8),
        "excitation_energy_eV": round(vqd_gap_eV, 6),
        "excitation_wavelength_nm": wavelength_nm,
        "exact_ground_energy": round(exact_gs, 8),
        "exact_excited_energy": round(exact_ex, 8),
        "exact_excitation_eV": round(exact_gap * HARTREE_TO_EV, 6),
        "vqd_error_vs_exact_mHa": round(abs(vqd_gap - exact_gap) * 1000, 4),
        "gs_ex_overlap": round(overlap, 6),
        "n_qubits": 2,
        "method": "VQD (Variational Quantum Deflation)",
        "beta_penalty": 2.0,
        "ansatz": "RY_CNOT_RY",
        "hamiltonian_coefficients": H2_BK_COEFFICIENTS_074A,
        "reference": "Higgott et al., Quantum 3, 156 (2019)",
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "excited_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
