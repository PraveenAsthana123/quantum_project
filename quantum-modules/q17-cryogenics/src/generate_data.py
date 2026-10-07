#!/usr/bin/env python3
"""Cryogenics & Dilution Refrigerators — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# fridge_stages.csv
with open(DATA_DIR / "fridge_stages.csv", "w", newline="") as _f:
    _f.writelines(['stage,temp_K,cooling_power_uW,heat_load_uW,margin_uW\n', '300K plate,300,unlimited,500000,unlimited\n', '4K plate,4,1500000,50000,1450000\n', 'Still,0.8,1000,200,800\n', 'Cold plate,0.1,400,100,300\n', 'MC,0.02,400,50,350\n'])
print(f"  Saved → {DATA_DIR / "fridge_stages.csv"}")

print("Data generation complete.")
