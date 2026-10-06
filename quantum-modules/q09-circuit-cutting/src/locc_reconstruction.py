"""
locc_reconstruction.py — LOCC channel reconstruction for circuit cutting (Q09)
Implements: E[O] = sum_k c_k * E[O_k]
Runs N=1000 shot simulations per QPD subcircuit term.
Reconstructs full expectation value and computes variance.
"""

import json
import os
import numpy as np
from typing import List, Dict, Tuple


# QPD channels for gate cutting (same as subcircuit_decompose.py)
# Single-qubit channels to insert at cut sites: {channel_name: gate_list}
PAULI_CHANNELS = {
    "I": [],           # identity: nothing
    "X": ["x"],
    "Y": ["y"],
    "Z": ["z"],
    "H": ["h"],
    "S": ["s"],
    "S+X": ["s", "x"],
}

# Simplified 4-term decomposition for one CNOT wire cut:
# CNOT ~ 1/2[(I⊗I) + (I⊗Z) + (X⊗X) - (Y⊗Y)] scaled by appropriate c_k
# c_I_I = 0.5, c_I_Z = 0.5, c_X_X = 0.5, c_Y_Y = -0.5  (4-term decomposition)
LOCC_TERMS = [
    # (coefficient, ctrl_gate_seq, targ_gate_seq)
    (+0.5, [],    []),       # I ⊗ I
    (+0.5, [],    ["z"]),    # I ⊗ Z
    (+0.5, ["x"], ["x"]),   # X ⊗ X
    (-0.5, ["y"], ["y"]),   # Y ⊗ Y
]


def build_subcircuit(
    n_qubits: int, cut_qubit: int, extra_gates_before_meas: List[str],
    name: str, basis_change: str = "Z"
):
    """
    Build a subcircuit where extra gates are inserted at the cut qubit.
    basis_change: 'Z' (standard), 'X' (H before measure), 'Y' (S†H before measure)
    """
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n_qubits, n_qubits, name=name)

    if "A" in name:
        # Left subcircuit: GHZ-like
        qc.h(0)
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
        # Insert QPD channel on cut qubit
        for gate in extra_gates_before_meas:
            if gate == "x":
                qc.x(cut_qubit)
            elif gate == "y":
                qc.y(cut_qubit)
            elif gate == "z":
                qc.z(cut_qubit)
    else:
        # Right subcircuit: RY chain
        for q in range(n_qubits):
            qc.ry(np.pi / 4, q)
        # Insert QPD channel on entry qubit
        for gate in extra_gates_before_meas:
            if gate == "x":
                qc.x(cut_qubit)
            elif gate == "y":
                qc.y(cut_qubit)
            elif gate == "z":
                qc.z(cut_qubit)

    # Basis rotation before measurement
    if basis_change == "X":
        qc.h(cut_qubit)
    elif basis_change == "Y":
        qc.sdg(cut_qubit)
        qc.h(cut_qubit)

    qc.measure_all()
    return qc


def simulate_circuit(qc, shots: int = 1000, seed: int = 42) -> Dict:
    """Run circuit simulation and return counts."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    sim = AerSimulator(seed_simulator=seed)
    tc = transpile(qc, sim, optimization_level=0)
    return sim.run(tc, shots=shots).result().get_counts()


def counts_to_expectation(counts: Dict, n_qubits: int) -> float:
    """
    Compute <Z^⊗n> = sum_x (-1)^{parity(x)} P(x)
    """
    total = sum(counts.values())
    exp = 0.0
    for bitstr, count in counts.items():
        bits = bitstr[::-1].replace(" ", "")[:n_qubits]
        parity = sum(int(b) for b in bits) % 2
        exp += (1 - 2 * parity) * count / total
    return exp


def reconstruct_expectation(n_shots_per_term: int = 1000, n_qubits: int = 3) -> Dict:
    """
    Reconstruct E[O] = sum_k c_k * E_k[O_A] * E_k[O_B]
    for a single CNOT cut between qubit (n_qubits-1) of A and qubit 0 of B.
    """
    cut_qubit_a = n_qubits - 1  # last qubit of A
    cut_qubit_b = 0              # first qubit of B

    term_results = []
    reconstructed = 0.0
    all_exp_a = []
    all_exp_b = []
    all_coeffs = []

    for idx, (c_k, ctrl_gates, targ_gates) in enumerate(LOCC_TERMS):
        # Run subcircuit A with ctrl_gates on cut qubit
        qc_a = build_subcircuit(
            n_qubits, cut_qubit_a, ctrl_gates, name=f"subcircuit_A_k{idx}", basis_change="Z"
        )
        counts_a = simulate_circuit(qc_a, shots=n_shots_per_term, seed=42 + idx)
        exp_a = counts_to_expectation(counts_a, n_qubits)

        # Run subcircuit B with targ_gates on cut qubit
        qc_b = build_subcircuit(
            n_qubits, cut_qubit_b, targ_gates, name=f"subcircuit_B_k{idx}", basis_change="Z"
        )
        counts_b = simulate_circuit(qc_b, shots=n_shots_per_term, seed=99 + idx)
        exp_b = counts_to_expectation(counts_b, n_qubits)

        contribution = c_k * exp_a * exp_b
        reconstructed += contribution

        all_coeffs.append(c_k)
        all_exp_a.append(exp_a)
        all_exp_b.append(exp_b)

        term_results.append({
            "term_idx": idx,
            "coefficient": c_k,
            "ctrl_gates": ctrl_gates,
            "targ_gates": targ_gates,
            "exp_a": round(exp_a, 4),
            "exp_b": round(exp_b, 4),
            "contribution": round(contribution, 4),
        })

    # Variance estimate: from shot noise per term
    # Var[E_k] ≈ (1 - E_k^2) / N_shots
    variance = 0.0
    for i, (c_k, exp_a, exp_b) in enumerate(zip(all_coeffs, all_exp_a, all_exp_b)):
        var_a = max(0.0, (1 - exp_a**2) / n_shots_per_term)
        var_b = max(0.0, (1 - exp_b**2) / n_shots_per_term)
        variance += (c_k**2) * (var_a + var_b)

    return {
        "reconstructed": round(reconstructed, 4),
        "variance": round(variance, 6),
        "std_error": round(variance**0.5, 6),
        "n_shots": n_shots_per_term,
        "term_results": term_results,
    }


def compute_exact_expectation(n_qubits: int = 6, shots: int = 16384) -> float:
    """
    Compute exact E[Z^⊗(2n)] on the full (2*n_qubits)-qubit circuit.
    Left half: GHZ, right half: RY chain, connected by CNOT at boundary.
    """
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    total = n_qubits * 2
    qc = QuantumCircuit(total)

    # Left GHZ
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)

    # Right RY chain
    for q in range(n_qubits, total):
        qc.ry(np.pi / 4, q)

    # Connection: CNOT(n_qubits-1, n_qubits)
    qc.cx(n_qubits - 1, n_qubits)

    qc.measure_all()

    sim = AerSimulator(seed_simulator=42)
    tc = transpile(qc, sim, optimization_level=0)
    counts = sim.run(tc, shots=shots).result().get_counts()

    return counts_to_expectation(counts, total)


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "locc_results.json")

    print("=== Q09 LOCC Channel Reconstruction ===")

    n_qubits_per_side = 3
    n_shots = 1000

    print(f"Circuit: 2x{n_qubits_per_side}-qubit = {2*n_qubits_per_side} total qubits")
    print(f"Cut: 1 CNOT between partition A (q{n_qubits_per_side-1}) and B (q{n_qubits_per_side})")
    print(f"QPD terms: {len(LOCC_TERMS)}, shots per term: {n_shots}\n")

    # Compute exact value
    print("Computing exact expectation value...")
    exact_value = compute_exact_expectation(n_qubits=n_qubits_per_side, shots=16384)
    print(f"Exact <Z^⊗{2*n_qubits_per_side}>: {exact_value:.4f}")

    # LOCC reconstruction
    print("Running LOCC reconstruction...")
    recon = reconstruct_expectation(n_shots_per_term=n_shots, n_qubits=n_qubits_per_side)
    reconstructed_value = recon["reconstructed"]
    relative_error = abs(reconstructed_value - exact_value) / (abs(exact_value) + 1e-10)

    print(f"Reconstructed: {reconstructed_value:.4f}")
    print(f"Variance: {recon['variance']:.6f}")
    print(f"Std error: {recon['std_error']:.6f}")
    print(f"Relative error: {relative_error:.4f} ({relative_error*100:.2f}%)")

    results = {
        "exact_value": round(exact_value, 4),
        "reconstructed_value": reconstructed_value,
        "n_shots": n_shots,
        "variance": recon["variance"],
        "relative_error": round(relative_error, 4),
        "std_error": recon["std_error"],
        "n_locc_terms": len(LOCC_TERMS),
        "total_shots_used": len(LOCC_TERMS) * n_shots * 2,
        "term_details": recon["term_results"],
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
