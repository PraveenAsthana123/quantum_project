#!/usr/bin/env python3
"""Quantum Many-Body Physics — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# phase_diagram.csv
with open(DATA_DIR / "phase_diagram.csv", "w", newline="") as _f:
    _f.writelines(['h_over_J,ground_energy,phase,entropy\n', '0.10,-4.0200,ferromagnetic,0.0693\n', '0.50,-4.4721,ferromagnetic,0.3465\n', '1.00,-5.6569,paramagnetic,0.6930\n', '1.50,-7.2111,paramagnetic,0.6930\n', '2.00,-8.9443,paramagnetic,0.6930\n'])
print(f"  Saved → {DATA_DIR / "phase_diagram.csv"}")

print("Data generation complete.")
