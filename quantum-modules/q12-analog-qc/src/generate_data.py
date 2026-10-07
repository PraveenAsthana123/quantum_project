#!/usr/bin/env python3
"""Analog Quantum Computing — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# qubo_problems.csv
with open(DATA_DIR / "qubo_problems.csv", "w", newline="") as _f:
    _f.writelines(['problem,nodes,edges,qubo_size,classical_opt,quantum_result,success_rate\n', 'max-cut-4,4,4,4,4,4,0.85\n', 'max-cut-8,8,12,8,6,5,0.72\n', 'tsp-5,5,10,25,15.2,16.1,0.65\n', 'portfolio-10,10,45,10,0.142,0.139,0.78\n'])
print(f"  Saved → {DATA_DIR / "qubo_problems.csv"}")

print("Data generation complete.")
