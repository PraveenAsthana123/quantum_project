"""
subcircuit_decompose.py — Subcircuit decomposition using LOCC channel expansion (Q09)
Takes an 8-qubit circuit with 3 CNOT cuts.
Decomposes using Pauli channel (LOCC) quasi-probability decomposition.
Computes reconstruction overhead = 9^k for k gate cuts.
"""

import json
import os
import numpy as np
from typing import List, Dict, Tuple


# -----------------------------------------------------------------------
# Gate cutting QPD: CNOT channel decomposition into local operations
# Following Mitarai & Fujii (PRL 2021):
#   CNOT = sum_{k=0}^{5} c_k * (A_k ⊗ B_k)
#   where A_k, B_k are single-qubit Pauli channels.
#   sum(|c_k|) = 3, overhead per cut = 3^2 = 9, total = 9^k.
# -----------------------------------------------------------------------

# QPD coefficients for CNOT (control, target)
# c_k, ctrl_channel, targ_channel, sign
CNOT_QPD = [
    (+0.5, "I",    "I",    +1),
    (+0.5, "I",    "Z",    +1),
    (+0.5, "Z",    "I",    +1),
    (-0.5, "Z",    "Z",    -1),
    (+0.5, "X",    "X",    +1),
    (+0.5, "Y",    "Y",    -1),
]

# L1 norm: sum(|c_k|) = 3.0, overhead per cut: 9


def build_8qubit_circuit():
    """
    Build 8-qubit circuit with 3 cross-partition CNOT cuts.
    Partition A: qubits 0-3
    Partition B: qubits 4-7
    Cut CNOTs: (3,4), (2,5), (1,6)
    """
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(8)

    # Partition A: GHZ preparation
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)

    # Partition B: RY rotation chain
    for q in range(4, 8):
        qc.ry(np.pi / 4, q)

    # Cross-partition cut CNOTs
    qc.cx(3, 4)   # cut 1
    qc.cx(2, 5)   # cut 2
    qc.cx(1, 6)   # cut 3

    return qc


def identify_cuts(circuit) -> List[Dict]:
    """Identify cross-partition gates (partition A = 0-3, B = 4-7)."""
    part_a = set(range(4))
    part_b = set(range(4, 8))
    cuts = []

    for i, inst in enumerate(circuit.data):
        gate_qubits = {q._index for q in inst.qubits}
        if gate_qubits & part_a and gate_qubits & part_b:
            ctrl = min(gate_qubits)
            targ = max(gate_qubits)
            cuts.append({
                "index": i,
                "gate": inst.operation.name,
                "control": ctrl,
                "target": targ,
                "partition_ctrl": "A",
                "partition_targ": "B",
            })
    return cuts


def build_subcircuit_a() -> "QuantumCircuit":
    """Build partition A (qubits 0-3) subcircuit without cross-partition gates."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(4, name="subcircuit_A")
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    # Cut qubit outputs: q1, q2, q3 send classical info to B
    return qc


def build_subcircuit_b() -> "QuantumCircuit":
    """Build partition B (qubits 4-7, re-indexed 0-3) subcircuit."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(4, name="subcircuit_B")
    for q in range(4):
        qc.ry(np.pi / 4, q)
    # Input qubits 0,1,2 receive channels from A cuts
    return qc


def compute_quasi_probability_coefficients(n_cuts: int) -> List[Dict]:
    """
    Compute all QPD coefficient tuples for n_cuts CNOT gates.
    Returns the Cartesian product of CNOT_QPD for each cut.
    Total terms = 6^n_cuts (before collapsing same channels).
    """
    from itertools import product

    all_terms = list(product(CNOT_QPD, repeat=n_cuts))
    coefficients = []
    for term in all_terms:
        c_total = 1.0
        channels_ctrl = []
        channels_targ = []
        for c_k, ctrl_ch, targ_ch, sign in term:
            c_total *= c_k
            channels_ctrl.append(ctrl_ch)
            channels_targ.append(targ_ch)
        if abs(c_total) > 1e-10:
            coefficients.append({
                "coefficient": round(c_total, 6),
                "ctrl_channels": channels_ctrl,
                "targ_channels": channels_targ,
            })

    # Compute overhead
    l1_per_cut = sum(abs(c) for c, _, _, _ in CNOT_QPD)
    overhead = l1_per_cut ** (2 * n_cuts)  # 9^k

    return coefficients, overhead


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "decompose_results.json")

    print("=== Q09 Subcircuit Decomposition ===")

    circuit = build_8qubit_circuit()
    print(f"Circuit: {circuit.num_qubits} qubits, depth={circuit.depth()}, "
          f"gates={dict(circuit.count_ops())}")

    cuts = identify_cuts(circuit)
    n_cuts = len(cuts)
    print(f"Found {n_cuts} cross-partition cuts:")
    for c in cuts:
        print(f"  Cut {c['index']}: {c['gate']}({c['control']},{c['target']}) "
              f"[{c['partition_ctrl']}→{c['partition_targ']}]")

    qc_a = build_subcircuit_a()
    qc_b = build_subcircuit_b()

    print(f"\nSubcircuit A: {qc_a.num_qubits} qubits, depth={qc_a.depth()}")
    print(f"Subcircuit B: {qc_b.num_qubits} qubits, depth={qc_b.depth()}")

    coefficients, overhead = compute_quasi_probability_coefficients(n_cuts)
    n_nonzero = len(coefficients)

    print(f"\nQPD coefficients: {n_nonzero} nonzero terms from {6**n_cuts} total")
    print(f"Reconstruction overhead: 9^{n_cuts} = {int(overhead)}")

    # Show top 10 by |coefficient|
    top_coeffs = sorted(coefficients, key=lambda x: abs(x["coefficient"]), reverse=True)[:10]

    results = {
        "n_qubits": 8,
        "n_cuts": n_cuts,
        "subcircuits": [
            {"name": "A", "n_qubits": 4, "depth": qc_a.depth(), "gates": dict(qc_a.count_ops())},
            {"name": "B", "n_qubits": 4, "depth": qc_b.depth(), "gates": dict(qc_b.count_ops())},
        ],
        "coefficients": top_coeffs,
        "total_qpd_terms": n_nonzero,
        "reconstruction_overhead": int(overhead),
        "overhead_formula": f"9^{n_cuts} = {int(overhead)}",
        "cuts": cuts,
        "l1_norm_per_cut": 3.0,
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
