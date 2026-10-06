"""
Blockchain PQC Lab — Synthetic Data Generator
===============================================
Purpose  : Generate four synthetic datasets for post-quantum blockchain demos.

Outputs (all written to ../data/)
---------------------------------
  wallet_registry.json      — 10 PQC wallets
  transactions.csv          — 500 signed transaction records
  cbdc_tokens.csv           — 200 CBDC token lifecycle records
  algorithm_benchmarks.json — Benchmark timings for 4 algorithms

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
random.seed(13)

# ── Paths ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

WALLET_JSON      = os.path.join(DATA_DIR, "wallet_registry.json")
TX_CSV           = os.path.join(DATA_DIR, "transactions.csv")
CBDC_CSV         = os.path.join(DATA_DIR, "cbdc_tokens.csv")
BENCH_JSON       = os.path.join(DATA_DIR, "algorithm_benchmarks.json")

# ── Algorithm specs ───────────────────────────────────────────────────────────
# Real FIPS 204/205 sizes and representative benchmark timings
ALGO_SPECS: Dict[str, Dict[str, Any]] = {
    "ECDSA-P256": {
        "quantum_safe":     False,
        "key_size_bytes":   64,       # 32-byte private + 64-byte public (uncompressed)
        "sig_size_bytes":   72,       # DER-encoded
        "keygen_ms":        0.05,
        "sign_ms":          0.06,
        "verify_ms":        0.12,
        "security_bits":    128,      # classical; 0 post-quantum (Shor breaks it)
        "pq_security_bits": 0,
    },
    "ML-DSA-65": {
        "quantum_safe":     True,
        "key_size_bytes":   1952,     # public key (FIPS 204)
        "sig_size_bytes":   3309,
        "keygen_ms":        0.35,
        "sign_ms":          0.80,
        "verify_ms":        0.30,
        "security_bits":    178,
        "pq_security_bits": 178,
    },
    "SLH-DSA-128f": {
        "quantum_safe":     True,
        "key_size_bytes":   32,       # public key (FIPS 205)
        "sig_size_bytes":   17088,
        "keygen_ms":        4.20,
        "sign_ms":          7.50,
        "verify_ms":        1.80,
        "security_bits":    128,
        "pq_security_bits": 128,
    },
    "FALCON-512": {
        "quantum_safe":     True,
        "key_size_bytes":   897,
        "sig_size_bytes":   666,
        "keygen_ms":        8.00,
        "sign_ms":          0.30,
        "verify_ms":        0.10,
        "security_bits":    103,
        "pq_security_bits": 103,
    },
}

ALGOS      = list(ALGO_SPECS.keys())
PQ_ALGOS   = [a for a in ALGOS if ALGO_SPECS[a]["quantum_safe"]]

BASE_TIME  = datetime(2026, 1, 1)


def _ts(offset_hours: float) -> str:
    dt = BASE_TIME + timedelta(hours=offset_hours)
    return dt.isoformat() + "Z"


def _pq_address(idx: int, algo: str) -> str:
    prefix = "pq1" if ALGO_SPECS[algo]["quantum_safe"] else "bc1"
    return f"{prefix}{uuid.uuid4().hex[:28]}"


# ── Wallet registry ────────────────────────────────────────────────────────────

def generate_wallet_registry(n: int = 10) -> List[Dict[str, Any]]:
    wallets = []
    # Distribute algorithms across wallets
    algo_cycle = (ALGOS * (n // len(ALGOS) + 1))[:n]
    for i in range(n):
        algo = algo_cycle[i]
        spec = ALGO_SPECS[algo]
        wallets.append({
            "wallet_id":       f"WALLET-{uuid.uuid4().hex[:8].upper()}",
            "owner":           f"user-{i+1:03d}",
            "algorithm":       algo,
            "address":         _pq_address(i, algo),
            "public_key_bytes":spec["key_size_bytes"],
            "quantum_safe":    spec["quantum_safe"],
            "created_at":      _ts(i * 72),
            "balance_btc":     round(random.uniform(0.01, 10.0), 6),
        })
    with open(WALLET_JSON, "w") as fh:
        json.dump({"wallets": wallets, "count": n,
                   "generated_at": datetime.utcnow().isoformat() + "Z"}, fh, indent=2)
    print(f"[generate_data] Wrote {n} wallets → {WALLET_JSON}")
    return wallets


# ── Transactions ──────────────────────────────────────────────────────────────

def generate_transactions(wallets: List[Dict[str, Any]], n: int = 500) -> None:
    addresses = [w["address"] for w in wallets]
    fieldnames = ["tx_id", "sender", "recipient", "amount_btc", "algorithm",
                  "signature_size_bytes", "sign_time_ms", "verify_time_ms",
                  "timestamp", "confirmed"]

    with open(TX_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            sender, recipient = random.sample(addresses, 2)
            # Infer sender's wallet algorithm
            sender_wallet = next((w for w in wallets if w["address"] == sender),
                                 wallets[0])
            algo = sender_wallet["algorithm"]
            spec = ALGO_SPECS[algo]
            jitter = random.uniform(0.8, 1.4)
            writer.writerow({
                "tx_id":               f"TX-{uuid.uuid4().hex[:12].upper()}",
                "sender":              sender,
                "recipient":           recipient,
                "amount_btc":          round(random.uniform(0.0001, 2.0), 6),
                "algorithm":           algo,
                "signature_size_bytes":spec["sig_size_bytes"],
                "sign_time_ms":        round(spec["sign_ms"] * jitter, 3),
                "verify_time_ms":      round(spec["verify_ms"] * jitter, 3),
                "timestamp":           _ts(i * 0.4),
                "confirmed":           1 if random.random() < 0.98 else 0,
            })
    print(f"[generate_data] Wrote {n} transactions → {TX_CSV}")


# ── CBDC tokens ───────────────────────────────────────────────────────────────

def generate_cbdc_tokens(wallets: List[Dict[str, Any]], n: int = 200) -> None:
    addresses   = [w["address"] for w in wallets]
    denominations = [0.01, 0.10, 1.00, 10.00, 50.00, 100.00]
    issuers       = ["BoC-CBDC", "ECB-CBDC", "Fed-CBDC", "PBoC-CBDC"]
    fieldnames    = ["token_id", "denomination", "issuer", "holder",
                     "issued_at", "algorithm", "verified", "transferred"]

    with open(CBDC_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            transferred = 1 if random.random() < 0.35 else 0
            writer.writerow({
                "token_id":    f"CBDC-{uuid.uuid4().hex[:10].upper()}",
                "denomination":random.choice(denominations),
                "issuer":      random.choice(issuers),
                "holder":      random.choice(addresses),
                "issued_at":   _ts(i * 0.8),
                "algorithm":   random.choice(PQ_ALGOS),
                "verified":    1 if random.random() < 0.99 else 0,
                "transferred": transferred,
            })
    print(f"[generate_data] Wrote {n} CBDC tokens → {CBDC_CSV}")


# ── Algorithm benchmarks ──────────────────────────────────────────────────────

def generate_algorithm_benchmarks() -> None:
    benchmarks = {}
    for algo, spec in ALGO_SPECS.items():
        benchmarks[algo] = {
            "keygen_ms":       spec["keygen_ms"],
            "sign_ms":         spec["sign_ms"],
            "verify_ms":       spec["verify_ms"],
            "key_size_bytes":  spec["key_size_bytes"],
            "sig_size_bytes":  spec["sig_size_bytes"],
            "quantum_safe":    spec["quantum_safe"],
            "security_bits":   spec["security_bits"],
            "pq_security_bits":spec["pq_security_bits"],
        }
    with open(BENCH_JSON, "w") as fh:
        json.dump({"benchmarks": benchmarks,
                   "generated_at": datetime.utcnow().isoformat() + "Z",
                   "platform": "simulated-x86_64"}, fh, indent=2)
    print(f"[generate_data] Wrote algorithm benchmarks → {BENCH_JSON}")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate() -> None:
    wallets = generate_wallet_registry(10)
    generate_transactions(wallets, 500)
    generate_cbdc_tokens(wallets, 200)
    generate_algorithm_benchmarks()


if __name__ == "__main__":
    generate()
