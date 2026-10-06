"""
entanglement_forging.py — Entanglement forging for distributed VQE (Q08)
Splits a 4-qubit VQE-like ansatz into two 2-qubit circuits via Schmidt decomposition.
Compares full 4-qubit vs forged 2-qubit circuit results.

Reference: Huembeli & Dauphin, "Entanglement Forging with Generative Neural Networks"
           IBM: "Entanglement forging" (2022)

E_forged = sum_{mn} lambda_m * lambda_n * <psi_m|H_A|psi_n> * <phi_m|H_B|phi_n>
"""

import json
import os
import numpy as np
from typing import Dict, List, Tuple


def build_h2_hamiltonian_matrix() -> np.ndarray:
    """
    Build a simplified 4-qubit H2 molecular Hamiltonian (Jordan-Wigner mapped).
    Uses Pauli strings for H2 at equilibrium bond length (1.4 Bohr).
    Approximate values from STO-3G basis set.
    """
    # 4x4 Pauli matrix definitions
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)

    def kron4(a, b, c, d):
        return np.kron(np.kron(np.kron(a, b), c), d)

    # H2 Hamiltonian Pauli terms (simplified STO-3G, Jordan-Wigner)
    H = (
        -1.0523732 * kron4(I, I, I, I)
        + 0.3979374 * kron4(Z, I, I, I)
        + 0.3979374 * kron4(I, Z, I, I)
        - 0.0112801 * kron4(I, I, Z, I)
        - 0.0112801 * kron4(I, I, I, Z)
        + 0.1809312 * kron4(Z, Z, I, I)
        + 0.0497497 * kron4(I, Z, Z, I)
        + 0.0497497 * kron4(Z, I, I, Z)
        + 0.0112801 * kron4(I, I, Z, Z)
        + 0.1743207 * kron4(Z, I, Z, I)
        + 0.1743207 * kron4(I, Z, I, Z)
        + 0.1205449 * kron4(X, X, Y, Y)
        + 0.1205449 * kron4(Y, Y, X, X)
        - 0.1205449 * kron4(X, Y, Y, X)
        - 0.1205449 * kron4(Y, X, X, Y)
    )
    return H


def build_4qubit_ansatz(theta: float):
    """
    Build a 4-qubit hardware-efficient ansatz for VQE.
    Parameters: single rotation angle theta (simplified single-parameter ansatz).
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter

    qc = QuantumCircuit(4)
    # Initial HF-like state (two electrons in two lowest orbitals)
    qc.x(0)
    qc.x(1)
    # Rotation layer
    qc.ry(theta, 0)
    qc.ry(theta, 1)
    qc.ry(theta, 2)
    qc.ry(theta, 3)
    # Entanglement
    qc.cx(0, 1)
    qc.cx(2, 3)
    qc.cx(1, 2)
    return qc


def get_statevector(circuit) -> np.ndarray:
    """Compute statevector of the circuit."""
    from qiskit.quantum_info import Statevector
    sv = Statevector(circuit)
    return sv.data


def compute_energy_full(theta: float, H: np.ndarray) -> float:
    """Compute <psi(theta)|H|psi(theta)> for the full 4-qubit circuit."""
    qc = build_4qubit_ansatz(theta)
    psi = get_statevector(qc)
    energy = np.real(psi.conj() @ H @ psi)
    return float(energy)


def schmidt_decompose(psi: np.ndarray, n_qubits_a: int = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute Schmidt decomposition of |psi> across partition A (first n_a qubits) and B.
    |psi> = sum_k lambda_k |phi_k>_A |phi_k>_B

    Returns: lambdas (Schmidt coefficients), states_A, states_B
    """
    n_total = int(np.log2(len(psi)))
    dim_a = 2 ** n_qubits_a
    dim_b = 2 ** (n_total - n_qubits_a)

    # Reshape psi into matrix M[i_A, i_B]
    M = psi.reshape(dim_a, dim_b)

    # SVD: M = U * S * Vh
    U, S, Vh = np.linalg.svd(M, full_matrices=False)

    # Schmidt coefficients = singular values, states = columns of U and rows of Vh
    return S, U.T, Vh   # lambdas, {|phi_k>_A}, {|phi_k>_B}


def build_2qubit_subcircuits_for_forging(theta: float, k: int):
    """
    Build 2-qubit subcircuits for Schmidt component k.
    For entanglement forging, we run multiple 2-qubit circuits and combine classically.
    Returns the two 2-qubit state-prep circuits for Schmidt state k.
    """
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    # Get full ansatz statevector
    full_qc = build_4qubit_ansatz(theta)
    psi = get_statevector(full_qc)
    lambdas, states_a, states_b = schmidt_decompose(psi, n_qubits_a=2)

    # Schmidt state k: |phi_k>_A and |phi_k>_B
    state_a_k = states_a[k]  # 2-qubit state vector (dim=4)
    state_b_k = states_b[k]  # 2-qubit state vector (dim=4)

    # Use Qiskit initialize for state prep
    qc_a = QuantumCircuit(2, name=f"A_k{k}")
    qc_a.initialize(state_a_k, [0, 1])

    qc_b = QuantumCircuit(2, name=f"B_k{k}")
    qc_b.initialize(state_b_k, [0, 1])

    return qc_a, qc_b, lambdas[k]


def compute_2qubit_hamiltonian(H_4q: np.ndarray, subsystem: str) -> np.ndarray:
    """
    Extract 2-qubit reduced Hamiltonian for subsystem A or B.
    H_A = partial_trace_B(H), H_B = partial_trace_A(H)
    Simplified: use diagonal block approximation.
    """
    dim = 4  # 2-qubit subsystem
    H_2q = np.zeros((dim, dim), dtype=complex)

    if subsystem == "A":
        # Trace over B (qubits 2,3): H_A[i,j] = sum_k H_4q[ik, jk]
        for i in range(dim):
            for j in range(dim):
                for k in range(dim):
                    H_2q[i, j] += H_4q[i * dim + k, j * dim + k]
    else:  # B
        # Trace over A (qubits 0,1): H_B[i,j] = sum_k H_4q[ki, kj]
        for i in range(dim):
            for j in range(dim):
                for k in range(dim):
                    H_2q[i, j] += H_4q[k * dim + i, k * dim + j]

    return H_2q / dim  # normalize by subsystem dimension


def compute_energy_forged(theta: float, H: np.ndarray) -> Tuple[float, Dict]:
    """
    Compute energy via entanglement forging.
    E_forged = sum_{m,n} lambda_m * lambda_n * <phi_m|H_A|phi_n> * <phi_m|H_B|phi_n>
    """
    from qiskit.quantum_info import Statevector

    full_qc = build_4qubit_ansatz(theta)
    psi = get_statevector(full_qc)
    lambdas, states_a, states_b = schmidt_decompose(psi, n_qubits_a=2)

    # Keep only significant Schmidt components
    n_schmidt = np.sum(lambdas > 1e-6)
    lambdas = lambdas[:n_schmidt]
    states_a = states_a[:n_schmidt]
    states_b = states_b[:n_schmidt]

    H_A = compute_2qubit_hamiltonian(H, "A")
    H_B = compute_2qubit_hamiltonian(H, "B")

    energy_forged = 0.0
    for m in range(n_schmidt):
        for n in range(n_schmidt):
            term_a = np.real(states_a[m].conj() @ H_A @ states_a[n])
            term_b = np.real(states_b[m].conj() @ H_B @ states_b[n])
            energy_forged += lambdas[m] * lambdas[n] * term_a * term_b

    speedup_factor = 4 ** 2 / (n_schmidt ** 2)  # full 4q cost vs 2q cost

    return float(np.real(energy_forged)), {
        "n_schmidt_components": int(n_schmidt),
        "schmidt_values": lambdas.tolist(),
        "speedup_factor": round(speedup_factor, 2),
    }


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "forging_results.json")

    print("=== Q08 Entanglement Forging ===")
    print("Building H2 Hamiltonian (4-qubit, Jordan-Wigner STO-3G)...")

    H = build_h2_hamiltonian_matrix()
    print(f"Hamiltonian: {H.shape} matrix")

    # Optimize theta for full circuit
    from scipy.optimize import minimize_scalar

    print("Optimizing full 4-qubit VQE...")
    result_full = minimize_scalar(
        lambda t: compute_energy_full(t, H),
        bounds=(-np.pi, np.pi),
        method="bounded",
    )
    theta_opt = result_full.x
    full_energy = result_full.fun
    print(f"Full 4-qubit energy (optimal theta={theta_opt:.4f}): {full_energy:.6f} Ha")

    print("Computing forged 2-qubit energy...")
    forged_energy, forging_info = compute_energy_forged(theta_opt, H)
    print(f"Forged 2-qubit energy: {forged_energy:.6f} Ha")

    error = abs(forged_energy - full_energy)
    print(f"Absolute error: {error:.6f} Ha")
    print(f"Schmidt components used: {forging_info['n_schmidt_components']}")
    print(f"Speedup factor: {forging_info['speedup_factor']}x")

    results = {
        "full_energy": round(full_energy, 6),
        "forged_energy": round(forged_energy, 6),
        "error": round(error, 6),
        "speedup_factor": forging_info["speedup_factor"],
        "n_schmidt_components": forging_info["n_schmidt_components"],
        "schmidt_values": [round(v, 6) for v in forging_info["schmidt_values"]],
        "optimal_theta": round(theta_opt, 6),
        "hamiltonian": "H2 STO-3G Jordan-Wigner 4-qubit",
        "method": "Schmidt decomposition + partial trace Hamiltonians",
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
