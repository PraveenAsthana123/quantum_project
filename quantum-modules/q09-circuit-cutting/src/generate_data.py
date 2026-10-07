#!/usr/bin/env python3
"""Circuit Cutting & Knitting — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# cutting_overhead.csv
with open(DATA_DIR / "cutting_overhead.csv", "w", newline="") as _f:
    _f.writelines(['cuts,sampling_overhead,classical_ms,fidelity\n', '1,4,5,0.99\n', '2,16,45,0.97\n', '3,64,200,0.93\n', '4,256,1200,0.87\n'])
print(f"  Saved → {DATA_DIR / "cutting_overhead.csv"}")

print("Data generation complete.")
