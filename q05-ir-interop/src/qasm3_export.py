"""
Q05 — OpenQASM 3 Export/Import.

Creates a 4-qubit circuit, exports to QASM 3, re-imports and verifies
gate count matches. Also exports to QASM 2 for comparison.

Reference: /mnt/deepa/quantum/github/compiler/qir-spec
Saves results to data/qasm_results.json.
"""

import json
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit import qasm3, qasm2
from qiskit.quantum_info import Operator
import numpy as np

RESULTS_PATH = Path(__file__).parent.parent / "data" / "qasm_results.json"
DATA_DIR = Path(__file__).parent.parent / "data"


def build_test_circuit(n_qubits: int = 4) -> QuantumCircuit:
    """Build a representative 4-qubit circuit with diverse gate types."""
    qc = QuantumCircuit(n_qubits)
    # Layer 1: superposition
    qc.h(0)
    qc.h(2)
    # Layer 2: entanglement
    qc.cx(0, 1)
    qc.cx(2, 3)
    # Layer 3: single-qubit rotations
    qc.rz(1.57, 1)
    qc.rx(0.785, 3)
    # Layer 4: more entanglement
    qc.cx(1, 2)
    # Layer 5: phase gates
    qc.t(0)
    qc.s(2)
    qc.tdg(3)
    # Layer 6: more operations
    qc.cx(0, 3)
    qc.h(1)
    qc.rz(0.5, 2)
    return qc


def roundtrip_qasm3(qc: QuantumCircuit) -> tuple[QuantumCircuit, bool]:
    """Export to QASM3 string and reimport. Return (reimported_circuit, verified)."""
    qasm3_str = qasm3.dumps(qc)

    # Re-import from QASM3
    try:
        qc_reimported = qasm3.loads(qasm3_str)
        # Verify gate counts match
        orig_ops = dict(qc.count_ops())
        reimport_ops = dict(qc_reimported.count_ops())
        verified = (sum(orig_ops.values()) == sum(reimport_ops.values()))
        return qc_reimported, verified, qasm3_str
    except Exception as e:
        print(f"  [WARN] QASM3 reimport failed: {e}")
        return None, False, qasm3_str


def main():
    print("=" * 60)
    print("Q05 — OpenQASM 3 Export / Import")
    print("=" * 60)

    n_qubits = 4
    qc = build_test_circuit(n_qubits)
    circuit_gates = dict(qc.count_ops())
    total_gates = sum(circuit_gates.values())

    print(f"\n  Circuit:")
    print(f"    Qubits: {n_qubits}")
    print(f"    Gates : {circuit_gates}")
    print(f"    Depth : {qc.depth()}")
    print(qc.draw(output="text", fold=80))

    # QASM 3 export
    print("\n  Exporting to OpenQASM 3...")
    qasm3_str = qasm3.dumps(qc)
    print(f"  QASM3 string length: {len(qasm3_str)} chars")
    print(f"\n--- QASM3 ---\n{qasm3_str}\n---")

    # QASM 2 export
    print("  Exporting to OpenQASM 2...")
    try:
        qasm2_str = qasm2.dumps(qc)
        qasm2_len = len(qasm2_str)
    except Exception as e:
        print(f"  [WARN] QASM2 export failed: {e}")
        qasm2_str = ""
        qasm2_len = 0
    print(f"  QASM2 string length: {qasm2_len} chars")
    if qasm2_str:
        print(f"\n--- QASM2 ---\n{qasm2_str[:300]}\n---")

    # Round-trip verification
    print("\n  Round-trip: QASM3 → reimport → verify...")
    qc_reimported, roundtrip_ok, _ = roundtrip_qasm3(qc)
    if qc_reimported is not None:
        reimport_gates = dict(qc_reimported.count_ops())
        gate_count_match = (sum(reimport_gates.values()) == total_gates)
        print(f"  Reimported gates: {reimport_gates}")
        print(f"  Gate count match: {gate_count_match}")
    else:
        reimport_gates = {}
        gate_count_match = False

    # Save QASM files
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    qasm3_path = DATA_DIR / "circuit.qasm3"
    qasm2_path = DATA_DIR / "circuit.qasm2"
    qasm3_path.write_text(qasm3_str)
    if qasm2_str:
        qasm2_path.write_text(qasm2_str)
    print(f"\n  QASM3 saved → {qasm3_path}")
    if qasm2_str:
        print(f"  QASM2 saved → {qasm2_path}")

    data = {
        "circuit_qubits": n_qubits,
        "circuit_depth": qc.depth(),
        "circuit_gates": circuit_gates,
        "circuit_gate_count": total_gates,
        "qasm3_string_length": len(qasm3_str),
        "qasm2_string_length": qasm2_len,
        "roundtrip_verified": bool(roundtrip_ok),
        "gate_count_match": bool(gate_count_match),
        "reimported_gates": reimport_gates,
        "qasm3_file": str(qasm3_path),
        "qasm2_file": str(qasm2_path) if qasm2_str else None,
        "qasm3_snippet": qasm3_str[:300],
        "reference": "/mnt/deepa/quantum/github/compiler/qir-spec",
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
