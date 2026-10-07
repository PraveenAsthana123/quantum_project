#!/usr/bin/env python3
"""QC Cryptography Module — Synthetic data generator."""
import csv, json, random
from pathlib import Path
import numpy as np

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- kat_vectors.csv ---
rows=[
  ('ML-KEM-768','keygen','deadbeef00112233','...pk_bytes=1184...','PASS'),
  ('ML-KEM-768','encaps','pk_hex_sample','ct_1088bytes_ss_32bytes','PASS'),
  ('ML-KEM-768','decaps','dk_ct_hex','ss_32bytes','PASS'),
  ('ML-DSA-65','keygen','seed_hex','pk_1952_sk_4032','PASS'),
  ('ML-DSA-65','sign','sk_msg_hex','sig_3293bytes','PASS'),
  ('ML-DSA-65','verify','pk_msg_sig','True','PASS'),
  ('SLH-DSA-128f','keygen','seed_hex','pk_32_sk_64','PASS'),
  ('SLH-DSA-128f','sign','sk_msg','sig_49856bytes','PASS'),
  ('BB84','qkd','1000bits_random','sifted_key_480bits','PASS'),
  ('Grover','oracle','n4_target2','steps_1','PASS'),
]
with open(DATA_DIR/'kat_vectors.csv','w',newline='') as f:
  w=csv.writer(f); w.writerow(['algorithm','operation','input','output','status'])
  w.writerows(rows)
print(f"  Saved → {DATA_DIR / "kat_vectors.csv"}")

print("\nData generation complete.")
