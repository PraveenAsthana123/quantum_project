#!/usr/bin/env python3
"""PQC Control Tower — Synthetic data generator."""
import csv, json, random
from pathlib import Path
import numpy as np

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- layer_status.csv ---
import csv
layers = [
  ('L01','Physical','done',100,'AES-256','AES-256'),
  ('L02','MACsec','in-progress',45,'ECDSA-P256','ML-DSA-65'),
  ('L03','IPsec','planning',10,'DH-2048','ML-KEM-768'),
  ('L04','TLS','in-progress',35,'ECDH+ECDSA','ML-KEM-768+ML-DSA-65'),
  ('L05','Session','planning',5,'RSA-2048','ML-KEM-768'),
  ('L06','PKI','planning',10,'RSA-4096','SLH-DSA-128s'),
  ('L07','HTTPS','in-progress',40,'ECDH','ML-KEM-768'),
  ('L08','JWT','in-progress',40,'RS256','ML-DSA-65'),
  ('L09','DNS','not-started',0,'ECDSA','ML-DSA-65'),
  ('L10','SSH','in-progress',30,'ecdh-sha2-nistp256','mlkem768x25519'),
  ('L11','Email','not-started',0,'RSA-2048','ML-DSA-65'),
  ('L12','CodeSign','planning',5,'ECDSA-P256','SLH-DSA-128f'),
  ('L13','VPN','planning',8,'DH-2048','ML-KEM-768'),
  ('L14','HSM','in-progress',20,'RSA','ML-DSA-65'),
  ('L15','IAM','planning',5,'ECDSA','ML-DSA-65'),
  ('L16','API-Gateway','in-progress',40,'RS256','ML-DSA-65'),
  ('L17','Database','not-started',0,'AES-128','AES-256'),
  ('L18','Blockchain','planning',5,'ECDSA','ML-DSA-65'),
  ('L19','Container','not-started',0,'ECDSA','ML-DSA-65'),
  ('L20','IoT','not-started',0,'RSA-2048','ML-DSA-44'),
  ('L21','Mobile','not-started',0,'ECDSA','ML-DSA-65'),
  ('L22','Firmware','planning',5,'RSA-2048','SLH-DSA-128f'),
  ('L23','DevSecOps','in-progress',25,'ECDSA','ML-DSA-65'),
  ('L24','SIEM','planning',5,'RSA','ML-DSA-65'),
  ('L25','ZeroTrust','in-progress',30,'ECDSA','ML-DSA-65'),
  ('L26','KMS','in-progress',20,'RSA-2048','ML-KEM-768'),
  ('L27','Compliance','planning',10,'various','FIPS-203/204/205'),
  ('L28','Audit','not-started',0,'SHA-256','SHA-3-256'),
  ('L29','AI/ML','not-started',0,'RSA','ML-DSA-65'),
]
with open(DATA_DIR/'layer_status.csv','w',newline='') as f:
  w=csv.writer(f); w.writerow(['layer_id','layer_name','status','progress_pct','algo_current','algo_target'])
  for row in layers: w.writerow(row)
print(f"  Saved → {DATA_DIR / "layer_status.csv"}")

# --- hndl_risk.csv ---
systems = [
  ('S01','TLS Termination',9,6,54,'CRITICAL'),
  ('S02','Internal PKI',8,8,64,'CRITICAL'),
  ('S03','VPN Gateway',7,9,63,'CRITICAL'),
  ('S04','API Gateway JWT',6,4,24,'HIGH'),
  ('S05','Email Archive',8,12,96,'CRITICAL'),
  ('S06','SSH Bastion',5,6,30,'HIGH'),
  ('S07','Code Signing',7,18,126,'CRITICAL'),
  ('S08','Database Encryption',4,10,40,'HIGH'),
  ('S09','Session Tokens',2,1,2,'LOW'),
  ('S10','Health Records',10,8,80,'CRITICAL'),
]
with open(DATA_DIR/'hndl_risk.csv','w',newline='') as f:
  w=csv.writer(f); w.writerow(['system_id','system_name','sensitivity','months_to_migrate','hndl_score','risk_level'])
  for row in systems: w.writerow(row)
print(f"  Saved → {DATA_DIR / "hndl_risk.csv"}")

print("\nData generation complete.")
