#!/usr/bin/env python3
"""Cloud QPU Access — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# qpu_providers.csv
with open(DATA_DIR / "qpu_providers.csv", "w", newline="") as _f:
    _f.writelines(['provider,hardware,qubits,T1_us,T2_us,price_1000shots_usd,connectivity\n', 'IBM,Eagle,127,150,80,1.60,heavy-hex\n', 'IBM,Heron,133,200,120,3.00,heavy-hex\n', 'AWS,IonQ Aria,25,50000,1000,0.30,all-to-all\n', 'Azure,Quantinuum H2,32,100000,10000,0.065,all-to-all\n', 'Google,Sycamore,53,15,10,0.00,grid\n'])
print(f"  Saved → {DATA_DIR / "qpu_providers.csv"}")

print("Data generation complete.")
