"""
generate_data.py — qc-crypto-lab
Generates data/crypto_benchmark.csv and data/vulnerability_scan.csv.
Uses only stdlib (csv, random, pathlib). Seed=42 for reproducibility.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

RANDOM_SEED = 42
DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Algorithm catalogue
# ---------------------------------------------------------------------------
ALGORITHMS = [
    # (algorithm, family, key_size_bits, sig_size_bytes,
    #  keygen_ms, sign_ms, verify_ms, quantum_safe, nist_level)
    ("RSA-2048",       "RSA",        2048,    256,   120.00, 0.80,  0.05,  False, 0),
    ("RSA-4096",       "RSA",        4096,    512,   980.00, 4.20,  0.18,  False, 0),
    ("ECDSA-P256",     "ECC",         256,     64,     0.30, 0.20,  0.50,  False, 0),
    ("ECDSA-P384",     "ECC",         384,     96,     0.50, 0.35,  0.80,  False, 0),
    ("Ed25519",        "EdDSA",       255,     64,     0.05, 0.06,  0.12,  False, 0),
    ("X25519",         "ECDH",        255,      0,     0.05, 0.05,  0.05,  False, 0),
    ("ML-KEM-512",     "CRYSTALS-K",  800,   1568,    0.06, 0.07,  0.07,  True,  1),
    ("ML-KEM-768",     "CRYSTALS-K", 1184,   1088,    0.08, 0.09,  0.09,  True,  3),
    ("ML-KEM-1024",    "CRYSTALS-K", 1568,   1568,    0.13, 0.14,  0.14,  True,  5),
    ("ML-DSA-44",      "CRYSTALS-D", 1312,   2420,    0.09, 0.25,  0.09,  True,  2),
    ("ML-DSA-65",      "CRYSTALS-D", 1952,   3293,    0.14, 0.35,  0.14,  True,  3),
    ("ML-DSA-87",      "CRYSTALS-D", 2592,   4595,    0.21, 0.53,  0.21,  True,  5),
    ("SLH-DSA-128f",   "SPHINCS+",     32,  49856,    0.90,35.00,  5.20,  True,  1),
    ("SLH-DSA-128s",   "SPHINCS+",     32,   7856,   14.00, 1.10,  0.50,  True,  1),
    ("FALCON-512",     "NTRU",         897,    666,    9.00, 0.25,  0.15,  True,  1),
    ("AES-128",        "Symmetric",    128,      0,    0.00, 0.00,  0.00,  True,  1),
    ("AES-256",        "Symmetric",    256,      0,    0.00, 0.00,  0.00,  True,  5),
    ("SHA-256",        "Hash",         256,      0,    0.00, 0.00,  0.00,  True,  2),
    ("SHA-3-256",      "Hash",         256,      0,    0.00, 0.00,  0.00,  True,  2),
    ("SHAKE-256",      "XOF",          256,      0,    0.00, 0.00,  0.00,  True,  3),
]

# Systems for vulnerability scan
SYSTEM_NAMES = [
    "auth-service", "payment-gateway", "vpn-endpoint", "tls-terminator",
    "code-signing", "cert-authority", "key-exchange", "pqc-pilot",
    "data-signing", "legacy-vpn", "api-gateway", "database-tls",
    "firmware-sign", "token-service", "cloud-kms", "iot-device",
    "email-server", "backup-encrypt", "hr-portal", "trading-engine",
]

VULNERABLE_ALGORITHMS = [
    "RSA-2048", "RSA-4096", "ECDSA-P256", "ECDSA-P384",
    "Ed25519", "DH-2048", "DH-4096", "ECDH-P256",
]
SAFE_ALGORITHMS = [
    "ML-KEM-768", "ML-DSA-65", "SLH-DSA-128f", "AES-256-GCM",
    "SHA-3-256", "ML-KEM-1024", "ML-DSA-87",
]

REPLACEMENTS = {
    "RSA-2048":   "ML-DSA-65",
    "RSA-4096":   "ML-DSA-87",
    "ECDSA-P256": "ML-DSA-44",
    "ECDSA-P384": "ML-DSA-65",
    "Ed25519":    "ML-DSA-44",
    "DH-2048":    "ML-KEM-768",
    "DH-4096":    "ML-KEM-1024",
    "ECDH-P256":  "ML-KEM-768",
}

GROVER_IMPACT = {
    "AES-128": "key_bits/2=64",
    "AES-256": "key_bits/2=128",
    "SHA-256": "preimage=128",
    "RSA-2048": "none (Shor)",
}


def generate_crypto_benchmark() -> None:
    """Write data/crypto_benchmark.csv with 40 rows (20 base + 20 variants)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(RANDOM_SEED)

    fieldnames = [
        "algorithm", "family", "key_size_bits", "sig_size_bytes",
        "keygen_ms", "sign_ms", "verify_ms", "quantum_safe", "nist_level",
    ]

    rows = []
    # Base 20 algorithms
    for alg in ALGORITHMS:
        name, family, ks, ss, kg, sgn, ver, qs, lvl = alg
        # Add small jitter to timing values (±5%) for realism
        jitter = lambda v: round(v * (1 + rng.uniform(-0.05, 0.05)), 4) if v > 0 else 0.0
        rows.append({
            "algorithm":      name,
            "family":         family,
            "key_size_bits":  ks,
            "sig_size_bytes": ss,
            "keygen_ms":      jitter(kg),
            "sign_ms":        jitter(sgn),
            "verify_ms":      jitter(ver),
            "quantum_safe":   str(qs),
            "nist_level":     lvl,
        })

    # 20 additional rows: hardware variants (e.g., "ML-DSA-65-HW", "RSA-2048-SW")
    for i, alg in enumerate(ALGORITHMS):
        name, family, ks, ss, kg, sgn, ver, qs, lvl = alg
        hw_factor = rng.uniform(0.3, 0.8)  # hardware accelerated = faster
        jitter = lambda v: round(v * hw_factor * (1 + rng.uniform(-0.05, 0.05)), 4) if v > 0 else 0.0
        rows.append({
            "algorithm":      f"{name}-HW",
            "family":         family,
            "key_size_bits":  ks,
            "sig_size_bytes": ss,
            "keygen_ms":      jitter(kg),
            "sign_ms":        jitter(sgn),
            "verify_ms":      jitter(ver),
            "quantum_safe":   str(qs),
            "nist_level":     lvl,
        })

    out_path = DATA_DIR / "crypto_benchmark.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {out_path} — {len(rows)} rows")


def generate_vulnerability_scan() -> None:
    """Write data/vulnerability_scan.csv with 20 rows."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(RANDOM_SEED)

    fieldnames = [
        "system_id", "system_name", "algorithm_found", "key_size",
        "quantum_safe", "shor_vulnerable", "grover_impact",
        "recommended_replacement", "priority",
    ]

    all_algorithms = VULNERABLE_ALGORITHMS + SAFE_ALGORITHMS
    rows = []
    for i, sys_name in enumerate(SYSTEM_NAMES):
        alg = rng.choice(all_algorithms)
        qs = alg in SAFE_ALGORITHMS
        shor = not qs and alg not in ["AES-128", "AES-256", "SHA-256"]
        grover = GROVER_IMPACT.get(alg, "none" if qs else "partial")
        repl = REPLACEMENTS.get(alg, "already quantum-safe" if qs else "review")
        priority = "low" if qs else ("critical" if shor else "medium")
        key_size = rng.choice([128, 256, 384, 512, 1024, 2048, 4096]) if not qs else rng.choice([128, 256, 512])

        rows.append({
            "system_id":              f"SYS-{i+1:03d}",
            "system_name":            sys_name,
            "algorithm_found":        alg,
            "key_size":               key_size,
            "quantum_safe":           str(qs),
            "shor_vulnerable":        str(shor),
            "grover_impact":          grover,
            "recommended_replacement": repl,
            "priority":               priority,
        })

    out_path = DATA_DIR / "vulnerability_scan.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {out_path} — {len(rows)} rows")


def main() -> None:
    print("qc-crypto-lab data generation")
    generate_crypto_benchmark()
    generate_vulnerability_scan()
    print("Done.")


if __name__ == "__main__":
    main()
