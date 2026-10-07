#!/usr/bin/env python3
"""Quantum IR Interoperability — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ir_formats.csv
with open(DATA_DIR / "ir_formats.csv", "w", newline="") as _f:
    _f.writelines(['format,vendor,extension,qubit_model,status\n', 'OpenQASM 3.0,IBM/QASM,qasm,gate-based,standard\n', 'QIR,Microsoft,ll,gate-based,standard\n', 'Quil,Rigetti,quil,gate-based,supported\n', 'OpenQASM 2.0,IBM,qasm,gate-based,legacy\n'])
print(f"  Saved → {DATA_DIR / "ir_formats.csv"}")

print("Data generation complete.")
