#!/usr/bin/env python3
"""Quantum Repeaters — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# repeater_chain.csv
with open(DATA_DIR / "repeater_chain.csv", "w", newline="") as _f:
    _f.writelines(['nodes,distance_km,F_raw,F_purified,F_end_to_end,memory_ms\n', '2,100,0.80,0.94,0.88,10\n', '3,200,0.70,0.89,0.95,10\n', '5,500,0.60,0.82,0.91,50\n', '10,1000,0.50,0.71,0.85,200\n'])
print(f"  Saved → {DATA_DIR / "repeater_chain.csv"}")

print("Data generation complete.")
