#!/usr/bin/env python3
"""Quantum Transpilation — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# hardware_topologies.csv
with open(DATA_DIR / "hardware_topologies.csv", "w", newline="") as _f:
    _f.writelines(['hardware,qubits,connectivity,basis_gates,T1_us,T2_us\n', 'IBM Eagle,127,heavy-hex,CX+RZ+SX,150,80\n', 'IBM Heron,133,heavy-hex,CZ+RZ+SX,200,120\n', 'Google Sycamore,53,grid,CZ+SX,15,10\n', 'IonQ Aria,25,all-to-all,MS+Rz+Ry,50000,1000\n'])
print(f"  Saved → {DATA_DIR / "hardware_topologies.csv"}")

print("Data generation complete.")
