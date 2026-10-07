#!/usr/bin/env python3
"""Quantum Security Lab — Synthetic data generator."""
import csv, json, random
from pathlib import Path
import numpy as np

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- qkd_simulation.csv ---
rows = []
for trial in range(50):
  import numpy as np
  ab = np.random.randint(0,2,1000)
  bb = np.random.randint(0,2,1000)
  match = (ab==bb).sum()
  qber = round(np.random.uniform(0.01,0.05),4)
  rows.append([trial, 1000, int(match), round(match/1000,3), qber, qber<0.11])
with open(DATA_DIR/'qkd_simulation.csv','w',newline='') as f:
  w=csv.writer(f); w.writerow(['trial','alice_bits','sifted_bits','sift_rate','qber','secure'])
  w.writerows(rows)
print(f"  Saved → {DATA_DIR / "qkd_simulation.csv"}")

# --- quantum_threats.csv ---
threats = [
  ('RSA-2048','Asymmetric','Shor','CRITICAL','ML-KEM-768/ML-DSA-65'),
  ('ECDSA-P256','Asymmetric','Shor','CRITICAL','ML-DSA-65'),
  ('DH-2048','Key-Exchange','Shor','CRITICAL','ML-KEM-768'),
  ('ECDH-P256','Key-Exchange','Shor','CRITICAL','ML-KEM-768'),
  ('AES-128','Symmetric','Grover','MEDIUM','AES-256'),
  ('AES-256','Symmetric','Grover','LOW','None needed'),
  ('SHA-256','Hash','Grover','LOW','SHA-3-256'),
  ('SHA-1','Hash','Collision','CRITICAL','SHA-3-256'),
]
with open(DATA_DIR/'quantum_threats.csv','w',newline='') as f:
  w=csv.writer(f); w.writerow(['algorithm','type','attack','risk','replacement'])
  w.writerows(threats)
print(f"  Saved → {DATA_DIR / "quantum_threats.csv"}")

print("\nData generation complete.")
