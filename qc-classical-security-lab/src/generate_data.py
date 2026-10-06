"""
Classical Security Lab — Synthetic Data Generator
===================================================
Purpose  : Generate three synthetic datasets for classical cryptography
           quantum-risk scanning, CBOM generation, and migration planning.

Outputs (all written to ../data/)
---------------------------------
  crypto_inventory.json    — 100 cryptographic assets across 29 layers
  vulnerability_scan.csv   — 200 vulnerability findings
  migration_progress.csv   — 29 layers × 10 systems = 290 migration rows

Usage
-----
    python generate_data.py
"""
from __future__ import annotations

import csv
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

# ── Reproducible seed ─────────────────────────────────────────────────────────
random.seed(21)

# ── Paths ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

INVENTORY_JSON   = os.path.join(DATA_DIR, "crypto_inventory.json")
VULN_CSV         = os.path.join(DATA_DIR, "vulnerability_scan.csv")
MIGRATION_CSV    = os.path.join(DATA_DIR, "migration_progress.csv")

# ── Crypto distribution (matches brief: 30% RSA, 20% ECDSA, …) ───────────────
CRYPTO_DISTRIBUTION = [
    # (algorithm, quantum_vulnerable, pct, cvss_max, replacement)
    ("RSA-2048",    True,  30, 9.1, "ML-DSA-65"),
    ("ECDSA-P256",  True,  20, 8.8, "ML-DSA-65"),
    ("DH-2048",     True,  15, 8.5, "ML-KEM-768"),
    ("SHA-1",       True,  10, 7.2, "SHA3-256"),
    ("AES-128",     True,  10, 6.5, "AES-256"),
    ("ML-KEM-768",  False, 10, 0.0, "N/A — already PQC"),
    ("ML-DSA-65",   False,  5, 0.0, "N/A — already PQC"),
]

# 29 security layers
LAYERS = [
    "L01-PKI", "L02-TLS", "L03-VPN", "L04-SSH", "L05-JWT",
    "L06-CodeSign", "L07-EmailPGP", "L08-DBEncrypt", "L09-FileEncrypt",
    "L10-KeyMgmt", "L11-HSM", "L12-APIGateway", "L13-ContainerSign",
    "L14-FirmwareSign", "L15-CloudKMS", "L16-IdentityIAM", "L17-CertMgmt",
    "L18-NetworkSec", "L19-AppLayer", "L20-DataAtRest", "L21-Backup",
    "L22-Logging", "L23-SIEMSOAR", "L24-SoftwareSBOM", "L25-DevSecOps",
    "L26-IoT", "L27-Mobile", "L28-Payment", "L29-Compliance",
]

SYSTEMS = [f"SYS-{i:03d}" for i in range(1, 11)]

PRIORITIES = ["P0-CRITICAL", "P1-HIGH", "P2-MEDIUM", "P3-LOW"]
SYSTEM_NAMES = [
    "banking-core", "payment-gateway", "auth-service", "api-platform",
    "data-warehouse", "mobile-backend", "identity-service", "firmware-updater",
    "cloud-hsm", "compliance-portal",
]

BASE_DATE = datetime(2026, 1, 1)


def _ts(offset_days: float) -> str:
    dt = BASE_DATE + timedelta(days=offset_days)
    return dt.strftime("%Y-%m-%d")


# ── Crypto inventory ──────────────────────────────────────────────────────────

def generate_crypto_inventory(n: int = 100) -> List[Dict[str, Any]]:
    assets = []
    # Build weighted list
    algo_pool: List[str] = []
    for algo, vuln, pct, _, _ in CRYPTO_DISTRIBUTION:
        algo_pool.extend([algo] * pct)

    asset_id = 1
    for layer in LAYERS[:n // len(LAYERS) + 1]:
        if asset_id > n:
            break
        for _ in range(max(1, n // len(LAYERS))):
            if asset_id > n:
                break
            algo_entry = random.choice(CRYPTO_DISTRIBUTION)
            algo_name  = algo_entry[0]
            vuln       = algo_entry[1]
            assets.append({
                "asset_id":         f"CA-{asset_id:04d}",
                "layer":            layer,
                "algorithm":        algo_name,
                "quantum_vulnerable":vuln,
                "system":           random.choice(SYSTEM_NAMES),
                "discovery_date":   _ts(random.uniform(0, 300)),
                "key_size_bits":    {
                    "RSA-2048":2048,"ECDSA-P256":256,"DH-2048":2048,
                    "SHA-1":160,"AES-128":128,"ML-KEM-768":768,"ML-DSA-65":1952,
                }.get(algo_name, 256),
            })
            asset_id += 1

    with open(INVENTORY_JSON, "w") as fh:
        json.dump({"assets": assets, "count": len(assets),
                   "generated_at": datetime.utcnow().isoformat() + "Z"}, fh, indent=2)
    print(f"[generate_data] Wrote {len(assets)} assets → {INVENTORY_JSON}")
    return assets


# ── Vulnerability scan ────────────────────────────────────────────────────────

def generate_vulnerability_scan(assets: List[Dict[str, Any]], n: int = 200) -> None:
    fieldnames = ["finding_id", "asset_id", "algorithm", "vulnerable",
                  "cvss_score", "priority", "system_name", "discovery_date",
                  "pqc_replacement", "remediation_effort_days"]

    # Build a cvss/priority lookup
    algo_cvss = {e[0]: e[3] for e in CRYPTO_DISTRIBUTION}
    algo_repl = {e[0]: e[4] for e in CRYPTO_DISTRIBUTION}

    with open(VULN_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            asset   = random.choice(assets)
            algo    = asset["algorithm"]
            vuln    = asset["quantum_vulnerable"]
            base_cvss = algo_cvss.get(algo, 5.0)
            cvss    = round(base_cvss * random.uniform(0.85, 1.05), 1) if vuln else 0.0
            cvss    = min(10.0, cvss)
            if cvss >= 9.0:
                priority = "P0-CRITICAL"
            elif cvss >= 7.5:
                priority = "P1-HIGH"
            elif cvss >= 5.0:
                priority = "P2-MEDIUM"
            else:
                priority = "P3-LOW"
            writer.writerow({
                "finding_id":            f"VULN-{uuid.uuid4().hex[:8].upper()}",
                "asset_id":              asset["asset_id"],
                "algorithm":             algo,
                "vulnerable":            1 if vuln else 0,
                "cvss_score":            cvss,
                "priority":              priority,
                "system_name":           asset["system"],
                "discovery_date":        _ts(random.uniform(0, 280)),
                "pqc_replacement":       algo_repl.get(algo, "N/A"),
                "remediation_effort_days": random.randint(5, 180) if vuln else 0,
            })
    print(f"[generate_data] Wrote {n} findings → {VULN_CSV}")


# ── Migration progress ────────────────────────────────────────────────────────

def generate_migration_progress() -> None:
    fieldnames = ["row_id", "layer_id", "system", "current_algo",
                  "target_algo", "completion_pct", "deadline",
                  "status", "engineer_assigned"]

    algo_pairs = [
        ("RSA-2048",   "ML-DSA-65"),
        ("ECDSA-P256", "ML-DSA-65"),
        ("DH-2048",    "ML-KEM-768"),
        ("SHA-1",      "SHA3-256"),
        ("AES-128",    "AES-256"),
    ]

    row_id = 1
    with open(MIGRATION_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for layer in LAYERS:
            for system in SYSTEMS:
                current, target = random.choice(algo_pairs)
                pct = random.randint(0, 100)
                if pct == 100:
                    status = "COMPLETED"
                elif pct >= 50:
                    status = "IN_PROGRESS"
                elif pct > 0:
                    status = "STARTED"
                else:
                    status = "NOT_STARTED"
                writer.writerow({
                    "row_id":           row_id,
                    "layer_id":         layer,
                    "system":           system,
                    "current_algo":     current,
                    "target_algo":      target,
                    "completion_pct":   pct,
                    "deadline":         _ts(random.uniform(30, 730)),
                    "status":           status,
                    "engineer_assigned":f"eng-{random.randint(1,20):03d}",
                })
                row_id += 1
    print(f"[generate_data] Wrote {row_id-1} migration rows → {MIGRATION_CSV}")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate() -> None:
    assets = generate_crypto_inventory(100)
    generate_vulnerability_scan(assets, 200)
    generate_migration_progress()


if __name__ == "__main__":
    generate()
