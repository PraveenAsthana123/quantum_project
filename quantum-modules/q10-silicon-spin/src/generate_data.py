#!/usr/bin/env python3
"""Silicon Spin Qubits — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# spin_properties.csv
with open(DATA_DIR / "spin_properties.csv", "w", newline="") as _f:
    _f.writelines(['qubit_id,T1_ms,T2_ms,f01_GHz,gate_fidelity_1q,gate_fidelity_2q,init_fidelity,readout_fidelity\n', 'Q0,100,10,6.5,0.9995,0.995,0.999,0.99\n', 'Q1,95,9,6.3,0.9994,0.994,0.998,0.99\n', 'Q2,110,11,6.7,0.9996,0.996,0.999,0.991\n'])
print(f"  Saved → {DATA_DIR / "spin_properties.csv"}")

print("Data generation complete.")
