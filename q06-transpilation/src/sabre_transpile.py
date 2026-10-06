"""
sabre_transpile.py — SABRE hardware-aware transpilation for Q06
Uses Qiskit SABRE layout + routing on a 7-qubit coupling map (IBM-like).
Compares depth, SWAP count, and native gate overhead before/after transpilation.
"""

import json
import os

def build_ghz_circuit(n_qubits: int = 5):
    """Build an n-qubit GHZ-like circuit (H + chain of CNOTs)."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n_qubits)
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    qc.measure_all()
    return qc


def get_nairobi_coupling_map():
    """
    Return a 7-qubit IBM Nairobi-like coupling map.
    Nairobi topology: 0-1-3-5-6, with 1-2 and 3-4 branches.
    """
    try:
        from qiskit.providers.fake_provider import GenericBackendV2
        backend = GenericBackendV2(
            7,
            coupling_map=[
                [0, 1], [1, 0],
                [1, 2], [2, 1],
                [1, 3], [3, 1],
                [3, 4], [4, 3],
                [3, 5], [5, 3],
                [5, 6], [6, 5],
            ],
        )
        return backend
    except Exception as e:
        print(f"[WARN] GenericBackendV2 failed ({e}), using manual coupling map")
        return None


def count_swaps(circuit) -> int:
    """Count SWAP gates in a circuit."""
    return sum(1 for inst in circuit.data if inst.operation.name == "swap")


def count_cx(circuit) -> int:
    """Count CX/CNOT gates."""
    return sum(1 for inst in circuit.data if inst.operation.name in ("cx", "cnot"))


def main():
    from qiskit import QuantumCircuit, transpile
    from qiskit.transpiler import CouplingMap

    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "sabre_results.json")

    # --- Build original circuit ---
    n_qubits = 5
    original = build_ghz_circuit(n_qubits)
    original_depth = original.depth()
    original_gates = dict(original.count_ops())
    original_cx = count_cx(original)

    print("=== Q06 SABRE Transpilation ===")
    print(f"Original circuit: {n_qubits} qubits, depth={original_depth}, gates={original_gates}")

    # --- Define Nairobi-like 7-qubit coupling map ---
    nairobi_edges = [
        [0, 1], [1, 0],
        [1, 2], [2, 1],
        [1, 3], [3, 1],
        [3, 4], [4, 3],
        [3, 5], [5, 3],
        [5, 6], [6, 5],
    ]
    coupling_map = CouplingMap(nairobi_edges)

    # --- Transpile with SABRE layout + routing ---
    try:
        transpiled = transpile(
            original,
            coupling_map=coupling_map,
            basis_gates=["cx", "id", "rz", "sx", "x"],
            layout_method="sabre",
            routing_method="sabre",
            optimization_level=1,
            seed_transpiler=42,
        )

        transpiled_depth = transpiled.depth()
        transpiled_gates = dict(transpiled.count_ops())
        swaps = count_swaps(transpiled)
        transpiled_cx = count_cx(transpiled)
        cx_overhead = transpiled_cx - original_cx

        # Extract final layout mapping (virtual -> physical qubit)
        layout = {}
        if transpiled.layout and transpiled.layout.final_layout:
            for virt, phys in transpiled.layout.final_layout.get_virtual_bits().items():
                layout[str(virt)] = phys
        elif transpiled.layout and transpiled.layout.initial_layout:
            for virt, phys in transpiled.layout.initial_layout.get_virtual_bits().items():
                layout[str(virt)] = phys
        else:
            layout = {"note": "layout not available in this Qiskit version"}

        results = {
            "original_depth": original_depth,
            "transpiled_depth": transpiled_depth,
            "swaps": swaps,
            "cx_overhead": cx_overhead,
            "original_cx": original_cx,
            "transpiled_cx": transpiled_cx,
            "original_gates": original_gates,
            "transpiled_gates": transpiled_gates,
            "layout": layout,
            "coupling_map": nairobi_edges,
            "basis_gates": ["cx", "id", "rz", "sx", "x"],
        }

        print(f"Transpiled circuit: depth={transpiled_depth}, SWAPs={swaps}, CX overhead={cx_overhead}")
        print(f"Depth increase: {transpiled_depth - original_depth} layers")
        print(f"CX gates: {original_cx} -> {transpiled_cx} (+{cx_overhead})")
        print(f"Layout: {layout}")

    except Exception as e:
        print(f"[ERROR] Transpilation failed: {e}")
        results = {"error": str(e), "original_depth": original_depth}

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
