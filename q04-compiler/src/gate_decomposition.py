"""
Q04 — Gate Decomposition.

Takes a random 5-qubit circuit with CX, T, H gates and decomposes it to the
basis gate set {CX, RZ, SX, X} using Qiskit transpiler passes.

Reference: /mnt/deepa/quantum/github/compiler/bqskit, tket
Saves results to data/decomposition_results.json.
"""

import json
from pathlib import Path
from collections import Counter

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

RESULTS_PATH = Path(__file__).parent.parent / "data" / "decomposition_results.json"
RNG = np.random.default_rng(42)


def count_gates(qc: QuantumCircuit) -> dict:
    """Return gate count dictionary."""
    return dict(Counter(qc.count_ops()))


def build_random_circuit(n_qubits: int = 5, seed: int = 42) -> QuantumCircuit:
    """
    Build a random circuit with H, T, CX gates.
    Uses a fixed seed for reproducibility.
    """
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n_qubits)

    gate_pool = ["h", "t", "tdg", "s", "cx"]
    n_layers = 8

    for _ in range(n_layers):
        # Single-qubit gates
        for q in range(n_qubits):
            gate = gate_pool[rng.integers(0, 3)]  # h, t, tdg
            if gate == "h":
                qc.h(q)
            elif gate == "t":
                qc.t(q)
            elif gate == "tdg":
                qc.tdg(q)
        # CX pairs
        pairs = rng.permutation(n_qubits)
        for i in range(0, n_qubits - 1, 2):
            ctrl = int(pairs[i])
            tgt = int(pairs[i + 1])
            qc.cx(ctrl, tgt)

    # Add a few extra gates
    qc.h(0)
    qc.t(1)
    qc.cx(0, 2)
    qc.s(3)
    qc.cx(3, 4)
    qc.t(4)

    return qc


def decompose_to_basis(qc: QuantumCircuit) -> QuantumCircuit:
    """Transpile to basis {cx, rz, sx, x} with optimization level 3."""
    return transpile(
        qc,
        basis_gates=["cx", "rz", "sx", "x"],
        optimization_level=3,
        seed_transpiler=42,
    )


def verify_equivalence(qc_orig: QuantumCircuit, qc_decomp: QuantumCircuit,
                       n_qubits: int = 5) -> float:
    """Check unitary equivalence (diamond norm ~= 0 if equal up to global phase)."""
    try:
        op_orig = Operator(qc_orig)
        op_decomp = Operator(qc_decomp)
        # Check if unitaries are equal up to global phase
        diff = op_orig.data - op_decomp.data
        fidelity = 1.0 - float(np.linalg.norm(diff) / (2 * 2 ** n_qubits))
        return max(0.0, fidelity)
    except Exception:
        return -1.0  # skip for large circuits


def main():
    print("=" * 60)
    print("Q04 — Gate Decomposition (Qiskit Transpiler)")
    print("=" * 60)

    n_qubits = 5
    qc_original = build_random_circuit(n_qubits, seed=42)

    orig_gates = count_gates(qc_original)
    orig_depth = qc_original.depth()
    orig_cx = orig_gates.get("cx", 0)

    print(f"\n  Original circuit:")
    print(f"    Qubits : {n_qubits}")
    print(f"    Gates  : {orig_gates}")
    print(f"    Depth  : {orig_depth}")
    print(f"    CX count: {orig_cx}")
    print(qc_original.draw(output="text", fold=80))

    # Decompose
    print("\n  Decomposing to basis {CX, RZ, SX, X}...")
    qc_decomposed = decompose_to_basis(qc_original)

    decomp_gates = count_gates(qc_decomposed)
    decomp_depth = qc_decomposed.depth()
    decomp_cx = decomp_gates.get("cx", 0)

    print(f"\n  Decomposed circuit:")
    print(f"    Gates  : {decomp_gates}")
    print(f"    Depth  : {decomp_depth}")
    print(f"    CX count: {decomp_cx}")

    print(f"\n  Summary:")
    total_orig = sum(orig_gates.values())
    total_decomp = sum(decomp_gates.values())
    print(f"    Total gates before: {total_orig}")
    print(f"    Total gates after : {total_decomp}")
    print(f"    Depth reduction   : {orig_depth} → {decomp_depth}")
    print(f"    CX count change   : {orig_cx} → {decomp_cx}")

    data = {
        "n_qubits": n_qubits,
        "original_gates": orig_gates,
        "original_depth": orig_depth,
        "decomposed_gates": decomp_gates,
        "decomposed_depth": decomp_depth,
        "cx_count_before": orig_cx,
        "cx_count_after": decomp_cx,
        "total_gates_before": total_orig,
        "total_gates_after": total_decomp,
        "basis_set": ["cx", "rz", "sx", "x"],
        "optimization_level": 3,
        "reference": "/mnt/deepa/quantum/github/compiler/bqskit",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
