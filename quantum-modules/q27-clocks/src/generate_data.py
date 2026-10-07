#!/usr/bin/env python3
"""Quantum Optical Clocks — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# clock_comparison.csv
with open(DATA_DIR / "clock_comparison.csv", "w", newline="") as _f:
    _f.writelines(['clock_type,transition,freq_Hz,uncertainty,stability_1s,notes\n', 'Cs-fountain,microwave,9.19e9,2e-16,1e-13,SI second definition\n', 'Rb-fountain,microwave,6.83e9,5e-16,3e-13,backup primary\n', 'Yb-lattice,optical,5.18e14,3e-18,1e-16,best stability\n', 'Sr-lattice,optical,4.29e14,2e-18,1e-16,best accuracy\n', 'Al+-ion,optical,1.12e15,9e-19,1e-17,most accurate\n'])
print(f"  Saved → {DATA_DIR / "clock_comparison.csv"}")

print("Data generation complete.")
