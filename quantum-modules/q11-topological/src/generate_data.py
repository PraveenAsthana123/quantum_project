#!/usr/bin/env python3
"""Topological Qubits — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# topological_comparison.csv
with open(DATA_DIR / "topological_comparison.csv", "w", newline="") as _f:
    _f.writelines(['qubit_type,error_per_gate,T2_us,protection,status\n', 'transmon,0.001,100,none,production\n', 'silicon-spin,0.0005,10000,some,research\n', 'topological-majorana,1e-9,infinite,topological,experimental\n'])
print(f"  Saved → {DATA_DIR / "topological_comparison.csv"}")

print("Data generation complete.")
