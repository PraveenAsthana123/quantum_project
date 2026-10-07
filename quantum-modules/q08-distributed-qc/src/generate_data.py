#!/usr/bin/env python3
"""Distributed Quantum Computing — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# distributed_results.csv
with open(DATA_DIR / "distributed_results.csv", "w", newline="") as _f:
    _f.writelines(['circuit_qubits,nodes,qubits_per_node,teleport_gates,fidelity,overhead\n', '6,2,3,2,0.94,4x\n', '10,2,5,4,0.88,8x\n', '12,3,4,6,0.82,12x\n', '16,4,4,12,0.72,16x\n'])
print(f"  Saved → {DATA_DIR / "distributed_results.csv"}")

print("Data generation complete.")
