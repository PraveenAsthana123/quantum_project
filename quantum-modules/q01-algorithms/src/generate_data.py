#!/usr/bin/env python3
"""Q01 Algorithms — Generate benchmark data for Shor, Grover, VQE, QAOA."""
import sys, csv, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

import math
import numpy as np

# ── 1. Algorithm Benchmarks CSV ───────────────────────────────────────────

def quantum_steps_shor(n: int) -> int:
    """Approx quantum steps: O((log N)^2 log log N log log log N)."""
    logn = math.log2(n) if n > 1 else 1
    return max(1, int(logn**2 * math.log2(logn + 1)))

def classical_steps_trial_div(n: int) -> int:
    return int(math.sqrt(n))

rows_benchmarks = []
for N in [15, 21, 35, 77, 143, 221, 323, 437, 667, 899]:
    rows_benchmarks.append({
        "algorithm": "Shor",
        "problem_size": N,
        "classical_steps": classical_steps_trial_div(N),
        "quantum_steps": quantum_steps_shor(N),
        "speedup_factor": round(classical_steps_trial_div(N) / max(1, quantum_steps_shor(N)), 3),
        "qubits_needed": int(2 * math.log2(N)) + 3,
    })

for N in [4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]:
    classical = N // 2  # avg linear search
    quantum = max(1, int(math.ceil(math.pi / 4 * math.sqrt(N))))
    rows_benchmarks.append({
        "algorithm": "Grover",
        "problem_size": N,
        "classical_steps": classical,
        "quantum_steps": quantum,
        "speedup_factor": round(classical / quantum, 3),
        "qubits_needed": int(math.ceil(math.log2(N))),
    })

# VQE: iterations to convergence (estimated)
for n_qubits in [2, 4, 6, 8, 10, 12]:
    params = 2 * n_qubits
    rows_benchmarks.append({
        "algorithm": "VQE",
        "problem_size": n_qubits,
        "classical_steps": 2**n_qubits,  # full diagonalization
        "quantum_steps": params * 100,   # param shift gradient calls
        "speedup_factor": round(2**n_qubits / max(1, params * 100), 4),
        "qubits_needed": n_qubits,
    })

# QAOA: p layers * 2 params * shots
for nodes in [4, 6, 8, 10, 12, 14]:
    brute_force = 2**nodes
    qaoa_evals = 2 * nodes * 200  # p=2, gradient steps
    rows_benchmarks.append({
        "algorithm": "QAOA",
        "problem_size": nodes,
        "classical_steps": brute_force,
        "quantum_steps": qaoa_evals,
        "speedup_factor": round(brute_force / max(1, qaoa_evals), 4),
        "qubits_needed": nodes,
    })

benchmarks_path = DATA_DIR / "algorithm_benchmarks.csv"
with open(benchmarks_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["algorithm","problem_size","classical_steps","quantum_steps","speedup_factor","qubits_needed"])
    writer.writeheader()
    writer.writerows(rows_benchmarks)
print(f"Saved {len(rows_benchmarks)} rows → {benchmarks_path}")

# ── 2. Circuit Depths CSV ──────────────────────────────────────────────────

rng = np.random.default_rng(42)
rows_depths = []
for algo, base_depth, depth_scale in [("Shor", 50, 15), ("Grover", 10, 8), ("VQE", 20, 5), ("QAOA", 15, 10)]:
    for n in range(2, 12):
        depth = base_depth + depth_scale * n + rng.integers(0, 5)
        rows_depths.append({
            "algorithm": algo,
            "n_qubits": n,
            "circuit_depth": int(depth),
            "two_qubit_gates": int(depth * 0.4),
            "single_qubit_gates": int(depth * 0.6),
            "t_gates": int(depth * 0.2),
        })

depths_path = DATA_DIR / "circuit_depths.csv"
with open(depths_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["algorithm","n_qubits","circuit_depth","two_qubit_gates","single_qubit_gates","t_gates"])
    writer.writeheader()
    writer.writerows(rows_depths)
print(f"Saved {len(rows_depths)} rows → {depths_path}")

print("\nQ01 data generation complete.")
