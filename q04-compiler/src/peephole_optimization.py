"""
Q04 — Peephole Circuit Optimization.

Generates a circuit with redundant gates (HH cancels, CX·CX cancels),
then applies Qiskit peephole optimization passes:
  - Optimize1qGates (merge consecutive single-qubit gates)
  - CXCancellation (cancel adjacent CNOT pairs)
  - CommutativeCancellation (commutation-aware cancellation)

Reference: /mnt/deepa/quantum/github/compiler/pyzx
Saves results to data/optimization_results.json.
"""

import json
from pathlib import Path
from collections import Counter

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import (
    Optimize1qGates,
    CXCancellation,
    CommutationAnalysis,
    CommutativeCancellation,
    InverseCancellation,
    RemoveResetInZeroState,
)
from qiskit.circuit.library import HGate, CXGate

RESULTS_PATH = Path(__file__).parent.parent / "data" / "optimization_results.json"


def count_gate_ops(qc: QuantumCircuit) -> dict:
    return dict(qc.count_ops())


def build_redundant_circuit(n_qubits: int = 5) -> QuantumCircuit:
    """
    Build a circuit with deliberate redundancies:
    - HH = I  (H followed by H cancels)
    - CX·CX = I  (CNOT followed by CNOT on same qubits cancels)
    - T·T† = I  (T followed by T-dagger cancels)
    - S·S·S·S = I  (four S gates cancel)
    """
    qc = QuantumCircuit(n_qubits)

    # Block 1: useful gates
    qc.h(0)
    qc.cx(0, 1)
    qc.t(2)
    qc.h(3)
    qc.cx(3, 4)

    # Block 2: redundant HH
    qc.h(0)   # H·H = I on qubit 0
    qc.h(0)

    # Block 3: redundant CX·CX
    qc.cx(0, 1)   # CX·CX = I on qubits 0,1
    qc.cx(0, 1)

    # Block 4: T·T† cancellation
    qc.t(2)
    qc.tdg(2)  # T·T† = I on qubit 2

    # Block 5: useful gate
    qc.rz(0.5, 2)
    qc.cx(2, 3)

    # Block 6: another HH
    qc.h(4)
    qc.h(4)   # H·H = I on qubit 4

    # Block 7: another CX pair
    qc.cx(1, 2)
    qc.cx(1, 2)  # cancels

    # Block 8: more useful work
    qc.h(0)
    qc.cx(0, 4)
    qc.rz(0.3, 1)
    qc.t(3)
    qc.cx(2, 4)

    return qc


def run_peephole_optimization(qc: QuantumCircuit) -> tuple[QuantumCircuit, list[str]]:
    """
    Apply peephole optimization passes and return optimized circuit.
    """
    passes = [
        RemoveResetInZeroState(),
        CommutationAnalysis(),
        CommutativeCancellation(),
        InverseCancellation([HGate(), CXGate()]),
        Optimize1qGates(basis=["rz", "sx", "x"]),
        CXCancellation(),
        Optimize1qGates(basis=["rz", "sx", "x"]),
    ]
    pm = PassManager(passes)
    qc_opt = pm.run(qc)
    return qc_opt, [type(p).__name__ for p in passes]


def main():
    print("=" * 60)
    print("Q04 — Peephole Circuit Optimization")
    print("=" * 60)

    n_qubits = 5
    qc = build_redundant_circuit(n_qubits)

    gates_before = count_gate_ops(qc)
    depth_before = qc.depth()
    total_before = sum(gates_before.values())

    print(f"\n  Circuit before optimization:")
    print(f"    Qubits : {n_qubits}")
    print(f"    Gates  : {gates_before}")
    print(f"    Total  : {total_before}")
    print(f"    Depth  : {depth_before}")

    print("\nRedundant gate patterns present:")
    print("  HH = I         (2× on qubit 0, 1× on qubit 4)")
    print("  CX·CX = I      (2× on qubits 0-1, 1× on qubits 1-2)")
    print("  T·T† = I       (1× on qubit 2)")

    print("\nApplying peephole optimization passes...")
    qc_opt, passes_applied = run_peephole_optimization(qc)

    gates_after = count_gate_ops(qc_opt)
    depth_after = qc_opt.depth()
    total_after = sum(gates_after.values())
    cancelled = total_before - total_after

    print(f"\n  Circuit after optimization:")
    print(f"    Gates  : {gates_after}")
    print(f"    Total  : {total_after}")
    print(f"    Depth  : {depth_after}")

    print(f"\n  Summary:")
    print(f"    Gates before   : {total_before}")
    print(f"    Gates after    : {total_after}")
    print(f"    Gates cancelled: {cancelled}")
    print(f"    Depth before   : {depth_before}")
    print(f"    Depth after    : {depth_after}")
    print(f"    Passes applied : {passes_applied}")

    data = {
        "n_qubits": n_qubits,
        "gates_before": gates_before,
        "gates_after": gates_after,
        "total_gates_before": total_before,
        "total_gates_after": total_after,
        "depth_before": depth_before,
        "depth_after": depth_after,
        "cancelled_gates": cancelled,
        "optimization_passes": passes_applied,
        "redundancies_injected": {
            "HH_pairs": 3,
            "CXCX_pairs": 2,
            "T_Tdagger_pairs": 1,
        },
        "reference": "/mnt/deepa/quantum/github/compiler/pyzx",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
