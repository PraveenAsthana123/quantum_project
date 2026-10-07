#!/usr/bin/env python3
"""Qubit Readout — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# iq_data.csv
with open(DATA_DIR / "iq_data.csv", "w", newline="") as _f:
    _f.writelines(['shot_id,i_signal,q_signal,true_state,measured_state\n', '0,-1.220,0.666,0,0\n', '1,1.012,-0.310,1,1\n', '2,-0.236,-0.174,0,0\n', '3,1.468,-0.385,1,1\n', '4,-1.413,-0.521,0,0\n', '5,0.525,-0.597,1,1\n', '6,-0.790,-0.294,0,0\n', '7,0.628,0.242,1,1\n', '8,-1.458,-0.113,0,0\n', '9,1.298,0.134,1,1\n', '10,-1.081,0.253,0,0\n', '11,1.360,-0.042,1,1\n', '12,-1.416,-0.337,0,0\n', '13,0.886,-0.385,1,1\n', '14,-0.714,-0.075,0,0\n', '15,1.096,-0.139,1,1\n', '16,-1.270,-0.647,0,0\n', '17,1.046,0.372,1,1\n', '18,-0.996,0.229,0,0\n', '19,1.068,-0.038,1,1\n'])
print(f"  Saved → {DATA_DIR / "iq_data.csv"}")

print("Data generation complete.")
