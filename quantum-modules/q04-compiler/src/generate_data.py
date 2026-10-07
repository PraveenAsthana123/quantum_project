#!/usr/bin/env python3
"""Quantum Compiler — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# compilation_benchmarks.csv
with open(DATA_DIR / "compilation_benchmarks.csv", "w", newline="") as _f:
    _f.writelines(['circuit,gates_in,gates_out,depth_in,depth_out,reduction_pct\n', 'Bell-state,4,3,2,2,25%\n', 'QFT-8,56,42,24,18,25%\n', 'VQE-H2,120,84,45,33,27%\n', 'QAOA-5,200,140,80,58,28%\n'])
print(f"  Saved → {DATA_DIR / "compilation_benchmarks.csv"}")

print("Data generation complete.")
