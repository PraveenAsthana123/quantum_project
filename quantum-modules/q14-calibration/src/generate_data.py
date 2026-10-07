#!/usr/bin/env python3
"""Quantum Gate Calibration — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# rb_results.csv
with open(DATA_DIR / "rb_results.csv", "w", newline="") as _f:
    _f.writelines(['depth,avg_fidelity,std_fidelity\n', '1,0.99950,0.005\n', '2,0.99900,0.005\n', '4,0.99800,0.005\n', '8,0.99601,0.005\n', '16,0.99206,0.005\n', '32,0.98425,0.005\n', '64,0.96899,0.005\n'])
print(f"  Saved → {DATA_DIR / "rb_results.csv"}")

print("Data generation complete.")
