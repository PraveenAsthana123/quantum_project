#!/usr/bin/env python3
"""Qubit Fabrication — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# junction_params.csv
with open(DATA_DIR / "junction_params.csv", "w", newline="") as _f:
    _f.writelines(['wafer_id,area_um2,Ic_nA,Rn_Ohm,EJ_GHz,EC_GHz,ratio,freq_GHz\n', 'W01,0.052,31,7950,15.5,0.30,51.7,5.80\n', 'W02,0.054,32,7900,16.0,0.30,53.3,5.90\n', 'W03,0.056,33,7850,16.5,0.30,55.0,5.99\n', 'W04,0.058,34,7800,17.0,0.30,56.7,6.09\n', 'W05,0.060,35,7750,17.5,0.30,58.3,6.18\n', 'W06,0.062,36,7700,18.0,0.30,60.0,6.27\n', 'W07,0.064,37,7650,18.5,0.30,61.7,6.36\n', 'W08,0.066,38,7600,19.0,0.30,63.3,6.45\n', 'W09,0.068,39,7550,19.5,0.30,65.0,6.54\n', 'W10,0.070,40,7500,20.0,0.30,66.7,6.63\n'])
print(f"  Saved → {DATA_DIR / "junction_params.csv"}")

print("Data generation complete.")
