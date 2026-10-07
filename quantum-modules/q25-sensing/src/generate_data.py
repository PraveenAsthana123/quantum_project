#!/usr/bin/env python3
"""Quantum Sensing — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# sensing_comparison.csv
with open(DATA_DIR / "sensing_comparison.csv", "w", newline="") as _f:
    _f.writelines(['n_probes,sql_precision,hl_precision,improvement,application\n', '10,0.316,0.100,3.16x,magnetometry\n', '100,0.100,0.010,10x,gravimetry\n', '1000,0.0316,0.001,31.6x,atomic clock\n', '10000,0.01,0.0001,100x,LIGO\n'])
print(f"  Saved → {DATA_DIR / "sensing_comparison.csv"}")

print("Data generation complete.")
