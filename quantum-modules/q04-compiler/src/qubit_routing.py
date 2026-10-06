"""
Q04 — SABRE Qubit Routing.

Creates a 5-qubit logical circuit with all-to-all connectivity, then maps it
to a linear coupling map (0-1-2-3-4) using Qiskit's SABRE layout + routing.
Counts SWAP insertions added.

Reference: /mnt/deepa/quantum/github/compiler/mqt-qmap
Saves results to data/routing_results.json.
"""

import json
from pathlib import Path
from collections import Counter

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import SabreLayout, SabreSwap

RESULTS_PATH = Path(__file__).parent.parent / "data" / "routing_results.json"


def count_cx(qc: QuantumCircuit) -> int:
    return qc.count_ops().get("cx", 0) + qc.count_ops().get("swap", 0) * 3


def build_all_to_all_circuit(n_qubits: int = 5, seed: int = 7) -> QuantumCircuit:
    """
    Build a 5-qubit circuit where every pair of qubits interacts at least once.
    This is the worst case for linear coupling map routing.
    """
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n_qubits)

    # Initial superposition
    for q in range(n_qubits):
        qc.h(q)

    # All-to-all CX gates: every (i,j) pair with i < j
    pairs = [(i, j) for i in range(n_qubits) for j in range(i + 1, n_qubits)]
    rng.shuffle(pairs)
    for ctrl, tgt in pairs:
        qc.cx(ctrl, tgt)
        # Add single-qubit gates for depth
        qc.rz(rng.uniform(0, 2 * np.pi), ctrl)
        qc.rz(rng.uniform(0, 2 * np.pi), tgt)

    # Second layer: more CX pairs
    more_pairs = [(0, 4), (1, 3), (0, 3), (2, 4)]
    for ctrl, tgt in more_pairs:
        qc.cx(ctrl, tgt)

    return qc


def route_to_linear(qc: QuantumCircuit, n_qubits: int = 5) -> tuple[QuantumCircuit, dict]:
    """
    Route circuit to a linear coupling map 0-1-2-3-4.
    Uses SABRE layout and routing.
    Returns (routed_circuit, layout_dict).
    """
    # Linear coupling map
    coupling_map = CouplingMap.from_line(n_qubits)

    routed = transpile(
        qc,
        coupling_map=coupling_map,
        layout_method="sabre",
        routing_method="sabre",
        basis_gates=["cx", "rz", "sx", "x", "h"],
        optimization_level=1,  # minimal optimization to preserve SWAP visibility
        seed_transpiler=42,
    )
    return routed, coupling_map


def count_swaps(original: QuantumCircuit, routed: QuantumCircuit) -> int:
    """
    Estimate number of SWAP gates inserted.
    A SWAP decomposes to 3 CX gates, so:
      swaps_added = (routed_cx - original_cx) / 3  (approximately)
    """
    orig_ops = original.count_ops()
    routed_ops = routed.count_ops()

    orig_cx = orig_ops.get("cx", 0)
    routed_cx = routed_ops.get("cx", 0)
    routed_swap = routed_ops.get("swap", 0)

    # Direct SWAP count
    if routed_swap > 0:
        return routed_swap

    # Inferred from CX overhead
    extra_cx = routed_cx - orig_cx
    return max(0, extra_cx // 3)


def main():
    print("=" * 60)
    print("Q04 — SABRE Qubit Routing (Linear Coupling Map)")
    print("=" * 60)

    n_qubits = 5
    qc_logical = build_all_to_all_circuit(n_qubits, seed=7)

    logical_cx = qc_logical.count_ops().get("cx", 0)
    logical_depth = qc_logical.depth()
    logical_ops = dict(qc_logical.count_ops())

    print(f"\n  Logical circuit (all-to-all connectivity):")
    print(f"    Qubits : {n_qubits}")
    print(f"    Gates  : {logical_ops}")
    print(f"    CX count: {logical_cx}")
    print(f"    Depth   : {logical_depth}")
    print(f"\n  Coupling map: linear  0 — 1 — 2 — 3 — 4")

    print("\n  Applying SABRE routing...")
    qc_routed, coupling_map = route_to_linear(qc_logical, n_qubits)

    physical_cx = qc_routed.count_ops().get("cx", 0)
    physical_depth = qc_routed.depth()
    physical_ops = dict(qc_routed.count_ops())
    swaps_added = count_swaps(qc_logical, qc_routed)

    print(f"\n  Routed circuit (linear coupling map):")
    print(f"    Gates  : {physical_ops}")
    print(f"    CX count: {physical_cx}")
    print(f"    Depth   : {physical_depth}")
    print(f"    SWAPs added: {swaps_added}")

    print(f"\n  Summary:")
    print(f"    Logical CX  : {logical_cx}")
    print(f"    Physical CX : {physical_cx}")
    print(f"    SWAP overhead: {swaps_added} SWAPs ≈ {swaps_added * 3} extra CX")
    print(f"    Coupling map edges: {list(coupling_map.get_edges())}")

    # Layout information
    layout = qc_routed.layout
    layout_dict = {}
    if layout and layout.initial_layout:
        for virt, phys in layout.initial_layout.get_virtual_bits().items():
            layout_dict[str(virt)] = phys

    data = {
        "n_qubits": n_qubits,
        "coupling_map": "linear 0-1-2-3-4",
        "coupling_map_edges": list(coupling_map.get_edges()),
        "logical_cx_count": logical_cx,
        "physical_cx_count": physical_cx,
        "swaps_added": swaps_added,
        "logical_depth": logical_depth,
        "physical_depth": physical_depth,
        "logical_ops": logical_ops,
        "physical_ops": physical_ops,
        "layout": layout_dict,
        "routing_method": "SABRE",
        "layout_method": "SABRE",
        "reference": "/mnt/deepa/quantum/github/compiler/mqt-qmap",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
