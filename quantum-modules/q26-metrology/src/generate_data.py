#!/usr/bin/env python3
"""Quantum Metrology — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# metrology_precision.csv
with open(DATA_DIR / "metrology_precision.csv", "w", newline="") as _f:
    _f.writelines(['n_qubits,classical_prec,quantum_prec,enhancement,application\n', '5,0.447,0.200,2.24x,gyroscope\n', '10,0.316,0.100,3.16x,atomic clock\n', '20,0.224,0.050,4.47x,VLBI\n', '50,0.141,0.020,7.07x,gravitational wave\n'])
print(f"  Saved → {DATA_DIR / "metrology_precision.csv"}")

print("Data generation complete.")
