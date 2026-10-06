"""
cutting_benchmark.py — Benchmark circuit cutting overhead vs direct simulation (Q09)
Compares: direct statevector simulation vs circuit cutting for 6,8,10 qubit circuits.
Shows exponential overhead tradeoffs and identifies crossover point.
"""

import json
import os
import time
import numpy as np
from typing import Dict, List


def build_benchmark_circuit(n_qubits: int):
    """Build a layered circuit for benchmarking."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n_qubits)
    # Layer 1: Hadamard on all
    for q in range(n_qubits):
        qc.h(q)
    # Layer 2: CNOT chain
    for q in range(0, n_qubits - 1, 2):
        qc.cx(q, q + 1)
    # Layer 3: RY rotations
    for q in range(n_qubits):
        qc.ry(np.pi / 4, q)
    # Layer 4: CNOT chain (shifted)
    for q in range(1, n_qubits - 1, 2):
        qc.cx(q, q + 1)
    return qc


def time_direct_simulation(n_qubits: int, shots: int = 4096) -> Dict:
    """
    Time direct statevector simulation.
    Memory: 2^n_qubits complex128 = 16 * 2^n bytes.
    """
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    qc = build_benchmark_circuit(n_qubits)
    qc.measure_all()

    sim = AerSimulator(method="statevector", seed_simulator=42)
    tc = transpile(qc, sim, optimization_level=0)

    t0 = time.perf_counter()
    result = sim.run(tc, shots=shots).result()
    t1 = time.perf_counter()

    elapsed_ms = (t1 - t0) * 1000
    memory_mb = 16 * (2 ** n_qubits) / (1024 ** 2)

    return {
        "n_qubits": n_qubits,
        "method": "direct_statevector",
        "time_ms": round(elapsed_ms, 2),
        "memory_mb": round(memory_mb, 4),
        "shots": shots,
    }


def time_cutting_simulation(n_qubits: int, n_cuts: int = 2, shots_per_term: int = 512) -> Dict:
    """
    Time circuit cutting simulation.
    For n_cuts CNOT cuts: 9^n_cuts * 2 subcircuit runs.
    Each subcircuit has ~n_qubits/2 qubits.
    """
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    sub_qubits = n_qubits // 2
    n_terms = 6 ** n_cuts  # QPD terms (before collapsing)
    total_runs = n_terms * 2  # two subcircuits per term

    qc_sub = build_benchmark_circuit(sub_qubits)
    qc_sub.measure_all()

    sim = AerSimulator(method="statevector", seed_simulator=42)
    tc = transpile(qc_sub, sim, optimization_level=0)

    # Time one subcircuit run then extrapolate
    t0 = time.perf_counter()
    sim.run(tc, shots=shots_per_term).result()
    t1 = time.perf_counter()

    single_run_ms = (t1 - t0) * 1000
    total_time_ms = single_run_ms * total_runs  # extrapolated

    overhead_factor = 9 ** n_cuts
    sub_memory_mb = 16 * (2 ** sub_qubits) / (1024 ** 2)

    return {
        "n_qubits": n_qubits,
        "method": "circuit_cutting",
        "n_cuts": n_cuts,
        "subcircuit_qubits": sub_qubits,
        "n_terms": n_terms,
        "total_subcircuit_runs": total_runs,
        "single_run_ms": round(single_run_ms, 2),
        "time_ms": round(total_time_ms, 2),   # extrapolated total
        "memory_mb": round(sub_memory_mb, 4),  # per subcircuit
        "overhead_factor": overhead_factor,
        "shots_per_term": shots_per_term,
    }


def find_crossover(direct_results: List[Dict], cutting_results: List[Dict]) -> Dict:
    """
    Find the qubit count where cutting becomes faster than direct simulation.
    Crossover: where cutting_time < direct_time.
    """
    crossover_qubits = None
    for d, c in zip(direct_results, cutting_results):
        assert d["n_qubits"] == c["n_qubits"]
        if c["time_ms"] < d["time_ms"]:
            crossover_qubits = d["n_qubits"]
            break

    return {
        "crossover_qubits": crossover_qubits,
        "note": (
            "Cutting is faster when subcircuit simulation savings exceed QPD overhead. "
            "For small circuits, direct simulation is cheaper. "
            "Crossover depends on n_cuts and available memory."
        ),
    }


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "benchmark_results.json")

    print("=== Q09 Circuit Cutting Benchmark ===")
    print("Comparing: direct simulation vs circuit cutting for 6, 8, 10 qubit circuits")
    print()

    qubit_sizes = [6, 8, 10]
    direct_results = []
    cutting_results = []

    print(f"{'Qubits':<8} {'Direct (ms)':<14} {'Cutting (ms)':<15} "
          f"{'Direct Mem (MB)':<17} {'Cut Mem (MB)':<14} {'Overhead':<10}")
    print("-" * 80)

    for n in qubit_sizes:
        print(f"  Running n={n}...", end="", flush=True)

        # Direct simulation
        try:
            d_result = time_direct_simulation(n, shots=4096)
        except MemoryError:
            d_result = {"n_qubits": n, "method": "direct_statevector",
                        "time_ms": float("inf"), "memory_mb": 16 * (2**n) / (1024**2)}
            print(f"  [MemoryError for n={n} direct]", end="")

        # Circuit cutting (2 cuts)
        n_cuts = 2
        c_result = time_cutting_simulation(n, n_cuts=n_cuts, shots_per_term=512)

        direct_results.append(d_result)
        cutting_results.append(c_result)

        print(f"\r  {n:<8} {d_result['time_ms']:<14.2f} {c_result['time_ms']:<15.2f} "
              f"{d_result['memory_mb']:<17.4f} {c_result['memory_mb']:<14.4f} "
              f"{c_result['overhead_factor']:<10}")

    crossover = find_crossover(direct_results, cutting_results)

    print(f"\nCrossover: {crossover['crossover_qubits']} qubits")
    print(f"Note: {crossover['note']}")

    # Theoretical analysis
    print("\nTheoretical scaling:")
    print(f"  Direct simulation memory: O(2^n) -> exponential in n")
    print(f"  Cutting overhead: O(9^k) per k cuts -> manageable for small k")
    print(f"  Cutting memory: O(2^(n/2)) per subcircuit -> quadratic advantage")

    results = {
        "qubit_sizes": qubit_sizes,
        "direct_time_ms": [r["time_ms"] for r in direct_results],
        "cutting_time_ms": [r["time_ms"] for r in cutting_results],
        "memory_mb": [r["memory_mb"] for r in direct_results],
        "crossover_qubits": crossover["crossover_qubits"],
        "n_cuts_used": 2,
        "overhead_formula": "9^k for k CNOT gate cuts",
        "theoretical_direct_memory_exponent": "2^n",
        "theoretical_cutting_memory_exponent": "2^(n/2)",
        "detailed_direct": direct_results,
        "detailed_cutting": cutting_results,
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
