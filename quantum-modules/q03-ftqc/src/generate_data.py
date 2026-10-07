#!/usr/bin/env python3
"""Fault-Tolerant Quantum Computing — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# surface_codes.csv
with open(DATA_DIR / "surface_codes.csv", "w", newline="") as _f:
    _f.writelines(['distance,physical_qubits,logical_qubits,threshold,logical_error\n', '3,9,1,0.01,1e-4\n', '5,25,1,0.01,1e-8\n', '7,49,1,0.01,1e-12\n', '9,81,1,0.01,1e-16\n'])
print(f"  Saved → {DATA_DIR / "surface_codes.csv"}")

print("Data generation complete.")
