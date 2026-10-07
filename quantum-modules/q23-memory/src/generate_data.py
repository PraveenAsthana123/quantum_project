#!/usr/bin/env python3
"""Quantum Memory — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# memory_performance.csv
with open(DATA_DIR / "memory_performance.csv", "w", newline="") as _f:
    _f.writelines(['protocol,T_us,efficiency,fidelity,bandwidth_GHz,modes\n', 'AFC,100,0.90,0.98,1.0,1000\n', 'DLCZ,10,0.50,0.95,0.01,1\n', 'EIT,50,0.70,0.97,0.001,1\n', 'Gradient-echo,1000,0.87,0.96,0.5,100\n'])
print(f"  Saved → {DATA_DIR / "memory_performance.csv"}")

print("Data generation complete.")
