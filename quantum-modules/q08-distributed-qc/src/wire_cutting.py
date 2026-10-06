"""
wire_cutting.py — Wire cutting via quasi-probability decomposition (Q08)
Replaces quantum wires with classical communication using a QPD of the identity channel.

Wire cutting identity channel decomposition:
  I = (1/2) * sum_{P in {I,X,Y,Z}} (P† ⊗ P) * sign_factor
  This requires O(4^k) overhead for k wire cuts.
"""

import json
import os
import numpy as np
from typing import List, Dict, Tuple


# -----------------------------------------------------------------------
# Quasi-probability decomposition of the identity wire (Schmitt channel)
# I_wire = (1/2)[|0><0| ⊗ I + |1><1| ⊗ X + |0><0| ⊗ Y + |1><1| ⊗ Z] (schematic)
# More precisely the Pauli decomposition gives:
#   I = (1/2)[Tr(P†ρ) * P for P in {I,X,Y,Z}]
# The complete set of 4 terms with quasi-probabilities:
#   c_I=+1/2, c_X=+1/2, c_Y=-1/2, c_Z=+1/2  (coefficient x channel pairs)
# For k cuts: overhead = (sum|c_i|)^2k = 4^k
# -----------------------------------------------------------------------

WIRE_QPD = [
    # (coefficient, preparation_op, measurement_basis)
    (+0.5, "I",  "Z"),   # Identity: measure Z
    (+0.5, "X",  "X"),   # X preparation: measure X
    (-0.5, "Y",  "Y"),   # Y preparation: measure Y
    (+0.5, "Z",  "Z"),   # Z preparation: measure Z
]


def build_circuit_with_wire_cut():
    """
    Build a 6-qubit circuit where we cut wire on qubit 2->3 link.
    Left side (qubits 0-2): prepares state
    Right side (qubits 3-5): continues computation
    The wire cut replaces the quantum wire q2->q3 with classical comm.
    """
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(6)

    # Left side: create entangled state
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.rz(np.pi / 3, 2)

    # [WIRE CUT HERE: q2 -> q3]

    # Right side: continues from q3 (which logically = q2 after cut)
    qc.h(3)  # will be replaced by preparation from QPD
    qc.cx(3, 4)
    qc.cx(4, 5)
    qc.rz(np.pi / 6, 5)

    return qc


def apply_prep_gate(circuit, qubit: int, prep_op: str):
    """Apply preparation operation for QPD term."""
    if prep_op == "I":
        pass  # identity: no gate
    elif prep_op == "X":
        circuit.x(qubit)
    elif prep_op == "Y":
        circuit.y(qubit)
    elif prep_op == "Z":
        circuit.z(qubit)


def apply_meas_basis(circuit, qubit: int, meas_basis: str):
    """Apply basis rotation before measurement."""
    if meas_basis == "Z":
        pass  # standard Z basis
    elif meas_basis == "X":
        circuit.h(qubit)  # X basis: apply H before measure
    elif meas_basis == "Y":
        circuit.sdg(qubit)   # Y basis: apply S†H before measure
        circuit.h(qubit)


def run_left_subcircuit(prep_op: str, meas_basis: str, shots: int = 2048, seed: int = 42) -> float:
    """
    Run left subcircuit (qubits 0-2) and return <O_left>.
    Output qubit q2 is measured in meas_basis.
    """
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    qc = QuantumCircuit(3, 1)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.rz(np.pi / 3, 2)

    apply_meas_basis(qc, 2, meas_basis)
    qc.measure(2, 0)

    sim = AerSimulator(seed_simulator=seed)
    tc = transpile(qc, sim, optimization_level=0)
    counts = sim.run(tc, shots=shots).result().get_counts()

    # <O> = P(0) - P(1) for Z-type expectation
    p0 = counts.get("0", 0) / shots
    p1 = counts.get("1", 0) / shots
    return p0 - p1


def run_right_subcircuit(prep_op: str, shots: int = 2048, seed: int = 99) -> float:
    """
    Run right subcircuit (qubits 3-5, re-indexed 0-2).
    Input qubit 0 (was q3) prepared with prep_op.
    Measure <Z⊗Z⊗Z> on output.
    """
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    qc = QuantumCircuit(3, 3)
    apply_prep_gate(qc, 0, prep_op)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.rz(np.pi / 6, 2)
    qc.measure_all()

    sim = AerSimulator(seed_simulator=seed)
    tc = transpile(qc, sim, optimization_level=0)
    counts = sim.run(tc, shots=shots).result().get_counts()

    # <Z⊗Z⊗Z>
    exp_val = 0.0
    total = sum(counts.values())
    for bitstring, count in counts.items():
        bits = bitstring[::-1].replace(" ", "")[:3]
        parity = sum(int(b) for b in bits) % 2
        exp_val += (1 - 2 * parity) * count / total
    return exp_val


def compute_overhead(k_cuts: int) -> Dict:
    """
    Compute wire cutting overhead statistics.
    Overhead = (sum |c_i|)^2 for each cut.
    For our decomposition: sum|c_i| = |0.5|+|0.5|+|-0.5|+|0.5| = 2.0
    Overhead per cut: 2^2 = 4 (L1 norm squared).
    Total overhead: 4^k.
    """
    l1_norm = sum(abs(c) for c, _, _ in WIRE_QPD)  # = 2.0
    overhead_per_cut = l1_norm ** 2  # = 4.0
    total_overhead = overhead_per_cut ** k_cuts  # 4^k
    samples_needed = int(total_overhead * 1000)  # 1000 base samples
    # Time factor: relative to uncut circuit
    time_factor = total_overhead

    return {
        "cuts": k_cuts,
        "l1_norm": round(l1_norm, 4),
        "overhead_per_cut": int(overhead_per_cut),
        "overhead": int(total_overhead),
        "samples_needed": samples_needed,
        "estimated_time_factor": round(time_factor, 2),
    }


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "wire_cutting_results.json")

    print("=== Q08 Wire Cutting ===")
    k_cuts = 1
    overhead = compute_overhead(k_cuts)
    print(f"Wire cuts: {k_cuts}")
    print(f"QPD decomposition: {len(WIRE_QPD)} terms")
    print(f"Overhead: 4^{k_cuts} = {overhead['overhead']}x shots needed\n")

    # Reconstruct E[O] = sum_i c_i * E_left_i * E_right_i
    shots_per_term = 2048
    reconstructed = 0.0
    term_details = []

    print("Running QPD reconstruction...")
    for idx, (c_k, prep_op, meas_basis) in enumerate(WIRE_QPD):
        exp_left = run_left_subcircuit(prep_op, meas_basis, shots=shots_per_term, seed=42 + idx)
        exp_right = run_right_subcircuit(prep_op, shots=shots_per_term, seed=99 + idx)
        contribution = c_k * exp_left * exp_right
        reconstructed += contribution

        term_details.append({
            "term": idx,
            "coefficient": c_k,
            "prep_op": prep_op,
            "meas_basis": meas_basis,
            "exp_left": round(exp_left, 4),
            "exp_right": round(exp_right, 4),
            "contribution": round(contribution, 4),
        })
        print(f"  Term {idx} (c={c_k:+.1f}, prep={prep_op}, meas={meas_basis}): "
              f"E_L={exp_left:.3f}, E_R={exp_right:.3f}, contrib={contribution:.4f}")

    print(f"\nReconstructed expectation: {reconstructed:.4f}")

    results = {
        "cuts": overhead["cuts"],
        "overhead": overhead["overhead"],
        "samples_needed": overhead["samples_needed"],
        "estimated_time_factor": overhead["estimated_time_factor"],
        "n_qpd_terms": len(WIRE_QPD),
        "reconstructed_expectation": round(reconstructed, 4),
        "shots_per_term": shots_per_term,
        "total_shots": len(WIRE_QPD) * shots_per_term * 2,
        "term_details": term_details,
        "overhead_formula": "4^k where k = number of wire cuts",
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
