#!/usr/bin/env python3
"""Quantum Chip Packaging — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# package_specs.csv
with open(DATA_DIR / "package_specs.csv", "w", newline="") as _f:
    _f.writelines(['package_type,substrate,L_nH,C_fF,resonance_GHz,isolation_dB\n', 'wire-bond,alumina,2.0,50,0.5,30\n', 'flip-chip,silicon,0.1,10,12.5,40\n', '3D-integration,silicon,0.05,5,25.0,50\n'])
print(f"  Saved → {DATA_DIR / "package_specs.csv"}")

print("Data generation complete.")
