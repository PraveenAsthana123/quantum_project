"""
Cryptographic Inventory Scanner — generates a CBOM (Cryptographic Bill of Materials).
Scans a directory for TLS certificates, SSH keys, and code-signing artifacts.
Flags algorithms as quantum-vulnerable or quantum-safe.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"

# ---------------------------------------------------------------------------
# Algorithm classification
# ---------------------------------------------------------------------------

QUANTUM_VULNERABLE = {
    "RSA", "DSA", "DH", "ECDH", "ECDSA", "EC", "ELGAMAL",
    "3DES", "DES", "RC4",  # also classically weak
}

QUANTUM_SAFE = {
    "ML-KEM", "ML-DSA", "SLH-DSA",  # NIST PQC standards
    "KYBER", "DILITHIUM", "FALCON", "SPHINCS+",  # older names still in use
    "AES-128", "AES-192", "AES-256",  # symmetric — quantum-weakened but usable at 256
    "SHA-256", "SHA-384", "SHA-512",
}

HARVEST_NOW_RISK = {"RSA", "ECDSA", "ECDH", "EC"}  # high-value targets for HNDL


@dataclass
class CryptoAsset:
    path: str
    asset_type: str           # certificate | ssh_key | pgp_key | code_signing | unknown
    algorithm: str
    key_size: Optional[int]
    subject: str
    issuer: str
    expiry: Optional[str]
    quantum_safe: bool
    harvest_now_risk: bool
    migration_priority: str   # P1 / P2 / P3
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout + r.stderr
    except Exception:
        return ""


def parse_certificate(path: Path) -> Optional[CryptoAsset]:
    out = _run(["openssl", "x509", "-in", str(path), "-noout",
                "-subject", "-issuer", "-enddate", "-pubkey"])
    if not out:
        return None

    subject = issuer = expiry = algorithm = ""
    key_size = None

    for line in out.splitlines():
        if line.startswith("subject"):
            subject = line.split("=", 1)[1].strip() if "=" in line else ""
        elif line.startswith("issuer"):
            issuer = line.split("=", 1)[1].strip() if "=" in line else ""
        elif "notAfter" in line or "Not After" in line.lower():
            expiry = line.split("=", 1)[1].strip() if "=" in line else ""
        elif "Public Key Algorithm" in line:
            algorithm = line.split(":")[1].strip().upper() if ":" in line else ""
        elif "Public-Key:" in line or "RSA Public-Key:" in line:
            m = line.strip()
            nums = [c for c in m if c.isdigit()]
            if nums:
                key_size = int("".join(nums))

    # Determine algorithm from pubkey info fallback
    if not algorithm:
        pubkey_out = _run(["openssl", "x509", "-in", str(path), "-noout", "-text"])
        for line in pubkey_out.splitlines():
            if "RSA" in line.upper():
                algorithm = "RSA"; break
            elif "ECDSA" in line.upper() or "EC" in line.upper():
                algorithm = "ECDSA"; break
            elif "ML-KEM" in line.upper() or "ML-DSA" in line.upper():
                algorithm = "ML-DSA"; break

    if not algorithm:
        algorithm = "UNKNOWN"

    alg_upper = algorithm.upper().replace("-", "").replace("WITH", "")
    quantum_safe = not any(v in alg_upper for v in QUANTUM_VULNERABLE)
    harvest = any(h in alg_upper for h in HARVEST_NOW_RISK)
    priority = "P1" if harvest else ("P2" if not quantum_safe else "P3")

    return CryptoAsset(
        path=str(path), asset_type="certificate",
        algorithm=algorithm, key_size=key_size,
        subject=subject, issuer=issuer, expiry=expiry,
        quantum_safe=quantum_safe, harvest_now_risk=harvest,
        migration_priority=priority,
    )


def parse_ssh_key(path: Path) -> Optional[CryptoAsset]:
    out = _run(["ssh-keygen", "-l", "-f", str(path)])
    if not out:
        return None

    parts = out.split()
    key_size = int(parts[0]) if parts and parts[0].isdigit() else None
    algorithm = parts[-1].strip("()").upper() if parts else "UNKNOWN"
    if "RSA" in algorithm:
        algorithm = "RSA"
    elif "ECDSA" in algorithm or "EC" in algorithm:
        algorithm = "ECDSA"
    elif "ED25519" in algorithm:
        algorithm = "ED25519"  # quantum-vulnerable (DLP on curve)

    quantum_safe = algorithm in QUANTUM_SAFE
    harvest = any(h in algorithm for h in HARVEST_NOW_RISK)
    priority = "P1" if harvest else ("P2" if not quantum_safe else "P3")

    return CryptoAsset(
        path=str(path), asset_type="ssh_key",
        algorithm=algorithm, key_size=key_size,
        subject="SSH Key", issuer="Local",
        expiry=None, quantum_safe=quantum_safe,
        harvest_now_risk=harvest, migration_priority=priority,
    )


def make_demo_assets() -> list[CryptoAsset]:
    """Generate a representative demo CBOM for demo/testing."""
    items = [
        ("web/server.crt", "certificate", "RSA", 2048, "CN=example.com", "CN=Let's Encrypt", "2025-03-15", False, True, "P1"),
        ("web/api.crt", "certificate", "ECDSA", 256, "CN=api.example.com", "CN=DigiCert", "2026-01-10", False, True, "P1"),
        ("ssh/id_rsa", "ssh_key", "RSA", 4096, "SSH Key", "Local", None, False, True, "P1"),
        ("ssh/id_ed25519", "ssh_key", "ED25519", 256, "SSH Key", "Local", None, False, False, "P2"),
        ("code_sign/release.crt", "code_signing", "ECDSA", 384, "CN=Release", "CN=Corp CA", "2027-06-01", False, True, "P1"),
        ("vault/config.crt", "certificate", "RSA", 2048, "CN=vault.internal", "CN=Internal CA", "2025-09-01", False, True, "P1"),
        ("pqc/kyber.cer", "certificate", "ML-KEM", 768, "CN=pqc.example.com", "CN=PQC CA", "2030-01-01", True, False, "P3"),
        ("pqc/dilithium.cer", "certificate", "ML-DSA", 2, "CN=pqc-sign", "CN=PQC CA", "2030-01-01", True, False, "P3"),
    ]
    assets = []
    for path, atype, alg, ks, subj, iss, exp, qs, harvest, prio in items:
        assets.append(CryptoAsset(
            path=path, asset_type=atype, algorithm=alg, key_size=ks,
            subject=subj, issuer=iss, expiry=exp,
            quantum_safe=qs, harvest_now_risk=harvest, migration_priority=prio,
        ))
    return assets


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

CERT_EXTENSIONS = {".crt", ".cer", ".pem", ".der"}
SSH_KEY_PATTERNS = {"id_rsa", "id_ecdsa", "id_ed25519", "id_dsa"}


def scan_directory(root: Path) -> list[CryptoAsset]:
    assets: list[CryptoAsset] = []
    for fpath in root.rglob("*"):
        if not fpath.is_file():
            continue
        suffix = fpath.suffix.lower()
        if suffix in CERT_EXTENSIONS:
            asset = parse_certificate(fpath)
            if asset:
                assets.append(asset)
        elif fpath.stem.lower() in SSH_KEY_PATTERNS and suffix in ("", ".pub"):
            asset = parse_ssh_key(fpath)
            if asset:
                assets.append(asset)
    return assets


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_cbom(assets: list[CryptoAsset], dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    cbom = {
        "cbom_version": "1.4",
        "generated": datetime.now(timezone.utc).isoformat(),
        "total_assets": len(assets),
        "quantum_vulnerable": sum(1 for a in assets if not a.quantum_safe),
        "quantum_safe": sum(1 for a in assets if a.quantum_safe),
        "harvest_now_risk": sum(1 for a in assets if a.harvest_now_risk),
        "assets": [a.to_dict() for a in assets],
    }
    json_path = dest / "cbom.json"
    with open(json_path, "w") as f:
        json.dump(cbom, f, indent=2)
    print(f"CBOM JSON → {json_path}")

    csv_path = dest / "cbom.csv"
    with open(csv_path, "w", newline="") as f:
        if assets:
            writer = csv.DictWriter(f, fieldnames=assets[0].to_dict().keys())
            writer.writeheader()
            for a in assets:
                writer.writerow(a.to_dict())
    print(f"CBOM CSV  → {csv_path}")
    return json_path, csv_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(scan_path: Optional[str] = None):
    if scan_path:
        target = Path(scan_path)
        if not target.exists():
            print(f"Path not found: {target}"); sys.exit(1)
        print(f"Scanning {target} for cryptographic assets...")
        assets = scan_directory(target)
        if not assets:
            print("No parseable crypto assets found — using demo CBOM")
            assets = make_demo_assets()
    else:
        print("No path supplied — generating demo CBOM")
        assets = make_demo_assets()

    print(f"\nFound {len(assets)} assets:")
    for a in assets:
        status = "✅ SAFE" if a.quantum_safe else "⚠️ VULNERABLE"
        print(f"  [{a.migration_priority}] {status} {a.asset_type:15s} {a.algorithm:12s} {a.path}")

    save_cbom(assets, DATA_DIR)
    return assets


if __name__ == "__main__":
    scan_target = sys.argv[1] if len(sys.argv) > 1 else None
    main(scan_target)
