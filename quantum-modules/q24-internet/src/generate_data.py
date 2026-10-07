#!/usr/bin/env python3
"""Quantum Internet — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# qkd_network.csv
with open(DATA_DIR / "qkd_network.csv", "w", newline="") as _f:
    _f.writelines(['link_id,node_a,node_b,distance_km,loss_dB_km,key_rate_bps\n', 'L01,Alice,Bob,10,0.2,50000\n', 'L02,Bob,Charlie,50,0.2,8000\n', 'L03,Charlie,Dave,100,0.2,1200\n', 'L04,Dave,Eve,200,0.2,50\n'])
print(f"  Saved → {DATA_DIR / "qkd_network.csv"}")

print("Data generation complete.")
