#!/usr/bin/env python3
"""Quantum Error Mitigation — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# mitigation_results.csv
with open(DATA_DIR / "mitigation_results.csv", "w", newline="") as _f:
    _f.writelines(['method,noise_level,raw_value,mitigated_value,error_reduction\n', 'ZNE,1x,0.60,0.50,16.7%\n', 'ZNE,2x,0.70,0.50,28.6%\n', 'ZNE,3x,0.80,0.50,37.5%\n', 'CDR,1x,0.62,0.51,17.7%\n', 'PEC,1x,0.60,0.50,16.7%\n'])
print(f"  Saved → {DATA_DIR / "mitigation_results.csv"}")

print("Data generation complete.")
