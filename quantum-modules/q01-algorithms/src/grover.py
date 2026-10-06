"""
Q01 — Grover's search algorithm.

Searches a database of N=8 items (3 qubits) for a marked target.
Tracks success probability vs. iteration count to show amplitude amplification.
Uses Qiskit with the statevector simulator.

Reference: /mnt/deepa/quantum/github/qiskit-tutorials/tutorials/algorithms/06_grover.ipynb
Saves results to data/grover_results.json.
"""

import json
import math
import time
from pathlib import Path

import numpy as np

RESULTS_PATH = Path(__file__).parent.parent / "data" / "grover_results.json"


# ── Oracle and diffuser (Qiskit) ──────────────────────────────────────────

def build_oracle(n_qubits: int, target: int) -> "QuantumCircuit":
    """Phase-flip oracle that marks |target⟩."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n_qubits, name="oracle")
    # Flip 0-bits so the target becomes |111…1⟩, apply multi-controlled Z, flip back
    target_bits = format(target, f"0{n_qubits}b")
    for i, bit in enumerate(reversed(target_bits)):
        if bit == "0":
            qc.x(i)
    # Multi-controlled Z via MCX + H
    qc.h(n_qubits - 1)
    qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
    qc.h(n_qubits - 1)
    for i, bit in enumerate(reversed(target_bits)):
        if bit == "0":
            qc.x(i)
    return qc


def build_diffuser(n_qubits: int) -> "QuantumCircuit":
    """Grover diffusion operator: 2|s⟩⟨s| - I."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n_qubits, name="diffuser")
    qc.h(range(n_qubits))
    qc.x(range(n_qubits))
    qc.h(n_qubits - 1)
    qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
    qc.h(n_qubits - 1)
    qc.x(range(n_qubits))
    qc.h(range(n_qubits))
    return qc


def run_grover(n_qubits: int, target: int, iterations: int) -> float:
    """Simulate Grover's algorithm for a given number of iterations.
    Returns the probability of measuring the target state."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    oracle = build_oracle(n_qubits, target)
    diffuser = build_diffuser(n_qubits)

    qc = QuantumCircuit(n_qubits)
    qc.h(range(n_qubits))  # uniform superposition

    for _ in range(iterations):
        qc.compose(oracle, inplace=True)
        qc.compose(diffuser, inplace=True)

    sv = Statevector.from_instruction(qc)
    probs = sv.probabilities()
    return float(probs[target])


def grover_optimal_iterations(n_qubits: int) -> int:
    """Theoretical optimal iterations ≈ π/4 * sqrt(N)."""
    N = 2 ** n_qubits
    return max(1, round(math.pi / 4 * math.sqrt(N)))


def main():
    print("=" * 60)
    print("Q01 — Grover's Search Algorithm (N=8, 3 qubits)")
    print("=" * 60)

    n_qubits = 3
    n_items = 2 ** n_qubits  # 8
    target = 6  # binary: 110
    max_iters = 5
    optimal_iters = grover_optimal_iterations(n_qubits)

    print(f"\n  Database size : N = {n_items}")
    print(f"  Target item   : {target} (binary: {format(target, f'0{n_qubits}b')})")
    print(f"  Optimal iters : {optimal_iters}")

    # Amplitude amplification trace
    print("\nSuccess probability vs iterations:")
    probs_per_iter = {}
    for k in range(1, max_iters + 1):
        p = run_grover(n_qubits, target, iterations=k)
        probs_per_iter[k] = round(p, 6)
        print(f"  k={k}: P(target) = {p:.4f}")

    # Classical queries needed on average: N/2
    classical_queries = n_items // 2
    quantum_queries = optimal_iters  # O(sqrt(N))
    success_probability = probs_per_iter[optimal_iters]

    print(f"\n  Classical queries (avg) : {classical_queries}")
    print(f"  Quantum queries (opt)   : {quantum_queries}")
    print(f"  P(success) at opt iter  : {success_probability:.4f}")
    print(f"  Quantum speedup factor  : {classical_queries / max(quantum_queries, 1):.2f}x")

    data = {
        "n_qubits": n_qubits,
        "n_items": n_items,
        "target": target,
        "target_binary": format(target, f"0{n_qubits}b"),
        "optimal_iterations": optimal_iters,
        "iterations_traced": max_iters,
        "probability_per_iteration": probs_per_iter,
        "success_probability": success_probability,
        "classical_queries": classical_queries,
        "quantum_queries": quantum_queries,
        "speedup_factor": round(classical_queries / max(quantum_queries, 1), 3),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
