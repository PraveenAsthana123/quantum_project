#!/usr/bin/env python3
"""Quantum Chemistry — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# molecules.csv
with open(DATA_DIR / "molecules.csv", "w", newline="") as _f:
    _f.writelines(['molecule,electrons,qubits,vqe_energy,fci_energy,error_mH,ansatz\n', 'H2,2,4,-1.137,-1.1373,0.3,UCCSD\n', 'LiH,4,12,-7.882,-7.8834,1.4,UCCSD\n', 'H2O,10,14,-76.24,-76.241,1.0,UCCSD\n', 'BeH2,6,14,-15.61,-15.611,1.0,UCCSD\n'])
print(f"  Saved → {DATA_DIR / "molecules.csv"}")

print("Data generation complete.")
