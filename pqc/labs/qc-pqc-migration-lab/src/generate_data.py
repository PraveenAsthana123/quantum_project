"""
PQC Migration Lab — Synthetic Data Generator
Generates crypto_assets.csv, migration_timeline.json, and benchmark_results.csv
into the data/ directory.

Usage: python src/generate_data.py
"""

import csv
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

# ── Reproducible seed ─────────────────────────────────────────────────────────
random.seed(42)

# ── Output directory ──────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# 1. crypto_assets.csv — 50 rows
# ─────────────────────────────────────────────────────────────────────────────

def generate_crypto_assets():
    """Generate 50 enterprise cryptographic assets across 6 algorithm types."""

    # (algorithm, key_size, quantum_safe, base_risk)
    ALGORITHM_POOL = [
        ("RSA-2048",   2048, False, "HIGH"),      # 20 rows
        ("RSA-4096",   4096, False, "MEDIUM"),     # 5 rows
        ("ECDSA-P256",  256, False, "HIGH"),       # 10 rows
        ("ECDH-P256",   256, False, "HIGH"),       # 8 rows
        ("AES-256",     256, True,  "LOW"),        # 5 rows
        ("SHA-256",     256, True,  "LOW"),        # 2 rows
    ]

    LOCATIONS = [
        "api-gateway", "internal-pki", "tls-terminator", "jwt-service",
        "ssh-bastion", "code-signing", "vpn-server", "email-server",
        "hsm-cluster", "database",
    ]

    USAGES = {
        "RSA-2048":   ["key_exchange", "signing", "certificate", "tls_cert"],
        "RSA-4096":   ["certificate", "code_signing", "root_ca"],
        "ECDSA-P256": ["signing", "tls_cert", "jwt_signing"],
        "ECDH-P256":  ["key_exchange", "ephemeral_dh"],
        "AES-256":    ["bulk_encryption", "data_at_rest", "session_encryption"],
        "SHA-256":    ["message_digest", "hmac"],
    }

    STATUSES = ["not-started", "planning", "in-progress", "testing", "done"]
    # Weights reflecting realistic enterprise state
    STATUS_WEIGHTS = [0.40, 0.25, 0.20, 0.10, 0.05]

    PHASES = {
        "not-started": "1-discovery",
        "planning":     "2-planning",
        "in-progress":  "3-hybrid-rollout",
        "testing":      "4-validation",
        "done":         "5-complete",
    }

    EFFORT_MAP = {
        "RSA-2048":   (5, 30),
        "RSA-4096":   (10, 45),
        "ECDSA-P256": (3, 20),
        "ECDH-P256":  (3, 20),
        "AES-256":    (1, 5),
        "SHA-256":    (1, 3),
    }

    # Build the 50-row dataset
    rows = []

    # Define exact counts per algorithm
    algo_counts = [
        ("RSA-2048",   20),
        ("RSA-4096",    5),
        ("ECDSA-P256", 10),
        ("ECDH-P256",   8),
        ("AES-256",     5),
        ("SHA-256",     2),
    ]

    asset_num = 1
    for algorithm, count in algo_counts:
        _, key_size, quantum_safe, base_risk = next(
            a for a in ALGORITHM_POOL if a[0] == algorithm
        )
        for _ in range(count):
            asset_id = f"A{asset_num:03d}"
            location = random.choice(LOCATIONS)
            usage    = random.choice(USAGES[algorithm])
            status   = random.choices(STATUSES, STATUS_WEIGHTS)[0]
            phase    = PHASES[status]

            # HNDL exposure: true for classical asymmetric algorithms in transit
            hndl = not quantum_safe and usage in (
                "key_exchange", "tls_cert", "certificate", "ephemeral_dh", "jwt_signing"
            )

            # Risk level: CRITICAL if HNDL + HIGH base_risk
            if hndl and base_risk == "HIGH":
                risk = "CRITICAL"
            elif not quantum_safe:
                risk = base_risk
            else:
                risk = "LOW"

            # Expiry: random date 1-5 years from now
            expiry = (
                datetime(2024, 1, 1) + timedelta(days=random.randint(180, 1825))
            ).strftime("%Y-%m-%d")

            effort_min, effort_max = EFFORT_MAP[algorithm]
            effort_days = random.randint(effort_min, effort_max)

            rows.append({
                "asset_id":             asset_id,
                "name":                 f"{location}-{usage}-{asset_num}",
                "algorithm":            algorithm,
                "key_size":             key_size,
                "usage":                usage,
                "location":             location,
                "expiry":               expiry,
                "risk_level":           risk,
                "hndl_exposure":        str(hndl).lower(),
                "migration_status":     status,
                "phase":                phase,
                "estimated_effort_days": effort_days,
            })
            asset_num += 1

    out_path = DATA_DIR / "crypto_assets.csv"
    fieldnames = [
        "asset_id", "name", "algorithm", "key_size", "usage", "location",
        "expiry", "risk_level", "hndl_exposure", "migration_status",
        "phase", "estimated_effort_days",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Generated {out_path}  ({len(rows)} rows)")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 2. migration_timeline.json
# ─────────────────────────────────────────────────────────────────────────────

def generate_migration_timeline():
    """Generate a CNSA 2.0 phased migration timeline."""

    timeline = {
        "generated": "2026-10-06",
        "standard": "CNSA 2.0 / NIST SP 800-208",
        "deadline": "2030",
        "phases": [
            {
                "phase": 1,
                "name": "Discovery & Inventory",
                "start": "2024-Q1",
                "end": "2024-Q4",
                "systems": 10,
                "milestones": [
                    "Complete CBOM across all 10 systems",
                    "Identify HNDL-exposed assets",
                    "Prioritize migration order by risk",
                    "Engage PQC library vendors (liboqs, BouncyCastle)",
                ],
                "status": "complete",
                "assets_inventoried": 50,
            },
            {
                "phase": 2,
                "name": "Hybrid Mode Rollout",
                "start": "2025-Q1",
                "end": "2026-Q2",
                "systems": 6,
                "milestones": [
                    "Deploy X25519+ML-KEM-768 in TLS terminator",
                    "Issue hybrid certificates from PQC CA",
                    "Enable ML-KEM-768 SSH host key exchange on ssh-bastion",
                    "Roll out ML-DSA-65 JWT signing in jwt-service",
                    "Validate interoperability with existing clients",
                ],
                "status": "in_progress",
                "assets_migrated": 12,
            },
            {
                "phase": 3,
                "name": "PQC Primary Mode",
                "start": "2026-Q3",
                "end": "2028-Q2",
                "systems": 8,
                "milestones": [
                    "Make PQC algorithms the default; classical as fallback",
                    "Complete HSM firmware upgrades to support ML-KEM/ML-DSA",
                    "Root CA ceremony with ML-DSA-65 root key",
                    "Deprecate RSA-2048 in new certificate issuance",
                    "CNSA 2.0 compliance audit",
                ],
                "status": "planned",
                "assets_migrated": 0,
            },
            {
                "phase": 4,
                "name": "Classical Deprecation",
                "start": "2028-Q3",
                "end": "2030-Q4",
                "systems": 10,
                "milestones": [
                    "Remove RSA/ECDSA fallback from TLS",
                    "Revoke all RSA-2048 certificates",
                    "Decommission classical SSH host keys",
                    "Archive legacy key material in HSM",
                    "Final CNSA 2.0 readiness certification",
                ],
                "status": "not_started",
                "assets_migrated": 0,
            },
        ],
        "protocol_timeline": {
            "TLS":          {"target_hybrid": "2025-Q1", "target_pqc_primary": "2027-Q1"},
            "PKI":          {"target_hybrid": "2025-Q3", "target_pqc_primary": "2027-Q4"},
            "SSH":          {"target_hybrid": "2025-Q2", "target_pqc_primary": "2027-Q2"},
            "JWT":          {"target_hybrid": "2025-Q4", "target_pqc_primary": "2028-Q1"},
            "Code Signing": {"target_hybrid": "2026-Q1", "target_pqc_primary": "2028-Q3"},
        },
    }

    out_path = DATA_DIR / "migration_timeline.json"
    with open(out_path, "w") as f:
        json.dump(timeline, f, indent=2)

    print(f"  Generated {out_path}")
    return timeline


# ─────────────────────────────────────────────────────────────────────────────
# 3. benchmark_results.csv — 20 rows
# ─────────────────────────────────────────────────────────────────────────────

def generate_benchmark_results():
    """Generate algorithm benchmark comparison data."""

    rows = [
        # Classical asymmetric — quantum-vulnerable
        {"algorithm": "RSA-2048",     "operation": "keygen",   "latency_ms":   0.50, "key_size_bytes":  256, "sig_size_bytes":  256, "quantum_safe": False},
        {"algorithm": "RSA-2048",     "operation": "sign",     "latency_ms":   0.30, "key_size_bytes":  256, "sig_size_bytes":  256, "quantum_safe": False},
        {"algorithm": "RSA-2048",     "operation": "verify",   "latency_ms":   0.01, "key_size_bytes":  256, "sig_size_bytes":  256, "quantum_safe": False},
        {"algorithm": "RSA-4096",     "operation": "keygen",   "latency_ms":   3.50, "key_size_bytes":  512, "sig_size_bytes":  512, "quantum_safe": False},
        {"algorithm": "RSA-4096",     "operation": "sign",     "latency_ms":   2.20, "key_size_bytes":  512, "sig_size_bytes":  512, "quantum_safe": False},
        {"algorithm": "ECDSA-P256",   "operation": "keygen",   "latency_ms":   0.08, "key_size_bytes":   64, "sig_size_bytes":   72, "quantum_safe": False},
        {"algorithm": "ECDSA-P256",   "operation": "sign",     "latency_ms":   0.10, "key_size_bytes":   64, "sig_size_bytes":   72, "quantum_safe": False},
        {"algorithm": "ECDSA-P256",   "operation": "verify",   "latency_ms":   0.15, "key_size_bytes":   64, "sig_size_bytes":   72, "quantum_safe": False},
        # NIST PQC Level 1 — ML-KEM-512
        {"algorithm": "ML-KEM-512",   "operation": "keygen",   "latency_ms":   0.03, "key_size_bytes":  800, "sig_size_bytes":  768, "quantum_safe": True},
        {"algorithm": "ML-KEM-512",   "operation": "encap",    "latency_ms":   0.04, "key_size_bytes":  800, "sig_size_bytes":  768, "quantum_safe": True},
        # NIST PQC Level 3 — ML-KEM-768 (primary recommendation)
        {"algorithm": "ML-KEM-768",   "operation": "keygen",   "latency_ms":   0.05, "key_size_bytes": 1184, "sig_size_bytes": 1088, "quantum_safe": True},
        {"algorithm": "ML-KEM-768",   "operation": "encap",    "latency_ms":   0.06, "key_size_bytes": 1184, "sig_size_bytes": 1088, "quantum_safe": True},
        {"algorithm": "ML-KEM-768",   "operation": "decap",    "latency_ms":   0.06, "key_size_bytes": 2400, "sig_size_bytes": 1088, "quantum_safe": True},
        # ML-DSA-65 (signature)
        {"algorithm": "ML-DSA-65",    "operation": "keygen",   "latency_ms":   0.18, "key_size_bytes": 1952, "sig_size_bytes": 3309, "quantum_safe": True},
        {"algorithm": "ML-DSA-65",    "operation": "sign",     "latency_ms":   0.50, "key_size_bytes": 4032, "sig_size_bytes": 3309, "quantum_safe": True},
        {"algorithm": "ML-DSA-65",    "operation": "verify",   "latency_ms":   0.28, "key_size_bytes": 1952, "sig_size_bytes": 3309, "quantum_safe": True},
        # SLH-DSA-128f (stateless hash-based — conservative option)
        {"algorithm": "SLH-DSA-128f", "operation": "keygen",   "latency_ms":   0.80, "key_size_bytes":   64, "sig_size_bytes": 17088, "quantum_safe": True},
        {"algorithm": "SLH-DSA-128f", "operation": "sign",     "latency_ms":  35.00, "key_size_bytes":   64, "sig_size_bytes": 17088, "quantum_safe": True},
        {"algorithm": "SLH-DSA-128f", "operation": "verify",   "latency_ms":   2.10, "key_size_bytes":   64, "sig_size_bytes": 17088, "quantum_safe": True},
        # X25519 (classical baseline for hybrid comparison)
        {"algorithm": "X25519",       "operation": "keygen",   "latency_ms":   0.02, "key_size_bytes":   32, "sig_size_bytes":    0, "quantum_safe": False},
    ]

    out_path = DATA_DIR / "benchmark_results.csv"
    fieldnames = [
        "algorithm", "operation", "latency_ms",
        "key_size_bytes", "sig_size_bytes", "quantum_safe",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Generated {out_path}  ({len(rows)} rows)")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\nPQC Migration Lab — Data Generator")
    print("=" * 45)
    print(f"Output directory: {DATA_DIR}")
    print()
    generate_crypto_assets()
    generate_migration_timeline()
    generate_benchmark_results()
    print()
    print("Data generation complete.")


if __name__ == "__main__":
    main()
