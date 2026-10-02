"""
Shared PQC utilities — reusable across all quantum projects.
Uses liboqs 0.16.0 (NIST FIPS 203/204/206 final names).

Install: pip install liboqs-python
Import:  from pqc_utils import kyber_kem, dilithium_sign, falcon_sign, assess_algorithm

Algorithm map (FIPS name → liboqs name):
  FIPS 203 ML-KEM-768   → 'ML-KEM-768'
  FIPS 204 ML-DSA-65    → 'ML-DSA-65'    (was Dilithium3)
  FIPS 206 FN-DSA-512   → 'Falcon-512'
"""
from __future__ import annotations
import json
import sys

# liboqs-python may conflict with the 'oqs' PyPI package — load directly
def _load_oqs():
    import importlib.util, pathlib
    candidates = [
        '/home/praveen/venv-ardupilot/lib/python3.13/site-packages/oqs/__init__.py',
        '/usr/local/lib/python3/dist-packages/oqs/__init__.py',
    ]
    for c in candidates:
        if pathlib.Path(c).exists():
            spec = importlib.util.spec_from_file_location('oqs_liboqs', c)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    try:
        import oqs as _oqs
        if hasattr(_oqs, 'KeyEncapsulation'):
            return _oqs
    except ImportError:
        pass
    return None


def kyber_kem(level: int = 768) -> dict:
    """
    FIPS 203 ML-KEM key encapsulation.
    level: 512 | 768 | 1024  (security level: 128 | 192 | 256 bit)
    """
    oqs = _load_oqs()
    if oqs is None:
        return {"error": "liboqs-python not found — run: pip install liboqs-python"}
    algo = f"ML-KEM-{level}"
    try:
        with oqs.KeyEncapsulation(algo) as kem:
            public_key = kem.generate_keypair()
            ciphertext, shared_secret_enc = kem.encap_secret(public_key)
            shared_secret_dec = kem.decap_secret(ciphertext)
        assert shared_secret_enc == shared_secret_dec, "KEM shared secret mismatch"
        return {
            "algorithm": f"{algo} (FIPS 203 ML-KEM)",
            "security_bits": level // 4,
            "public_key_bytes": len(public_key),
            "ciphertext_bytes": len(ciphertext),
            "shared_secret_hex": shared_secret_enc.hex()[:32] + "...",
            "kem_verified": True,
            "status": "REAL PQC — liboqs 0.16.0",
        }
    except Exception as e:
        return {"error": str(e), "algo": algo}


def dilithium_sign(message: bytes = b"quantum-safe payload", level: int = 65) -> dict:
    """
    FIPS 204 ML-DSA digital signature.
    level: 44 | 65 | 87  (was Dilithium2/3/5 → ML-DSA-44/65/87)
    """
    oqs = _load_oqs()
    if oqs is None:
        return {"error": "liboqs-python not found"}
    algo = f"ML-DSA-{level}"
    try:
        with oqs.Signature(algo) as signer:
            public_key = signer.generate_keypair()
            signature = signer.sign(message)
        with oqs.Signature(algo) as verifier:
            valid = verifier.verify(message, signature, public_key)
        return {
            "algorithm": f"{algo} (FIPS 204 ML-DSA)",
            "public_key_bytes": len(public_key),
            "signature_bytes": len(signature),
            "message": message.decode("utf-8", errors="replace"),
            "valid": valid,
            "status": "REAL PQC — liboqs 0.16.0",
        }
    except Exception as e:
        return {"error": str(e), "algo": algo}


def falcon_sign(message: bytes = b"artifact to sign", variant: str = "Falcon-512") -> dict:
    """
    FIPS 206 FN-DSA (Falcon) compact lattice signature.
    variant: 'Falcon-512' | 'Falcon-1024' | 'Falcon-padded-512'
    """
    oqs = _load_oqs()
    if oqs is None:
        return {"error": "liboqs-python not found"}
    try:
        with oqs.Signature(variant) as signer:
            pk = signer.generate_keypair()
            sig = signer.sign(message)
        with oqs.Signature(variant) as verifier:
            valid = verifier.verify(message, sig, pk)
        return {
            "algorithm": f"{variant} (FIPS 206 FN-DSA)",
            "public_key_bytes": len(pk),
            "signature_bytes": len(sig),
            "valid": valid,
            "status": "REAL PQC — liboqs 0.16.0",
        }
    except Exception as e:
        return {"error": str(e), "variant": variant}


def assess_algorithm(algo_name: str) -> dict:
    """Classify a classical algorithm's quantum vulnerability."""
    VULNERABLE = {
        "RSA-1024":  ("CRITICAL", "Shor's algorithm",          "ML-DSA-44 or ML-KEM-512"),
        "RSA-2048":  ("CRITICAL", "Shor's algorithm",          "ML-DSA-65 or ML-KEM-768"),
        "RSA-4096":  ("CRITICAL", "Shor's algorithm",          "Falcon-512 or ML-DSA-65"),
        "ECDSA-P256":("CRITICAL", "Shor's algorithm",          "ML-DSA-44"),
        "ECDSA-P384":("CRITICAL", "Shor's algorithm",          "ML-DSA-65"),
        "ECDH-P256": ("CRITICAL", "Shor's algorithm",          "ML-KEM-768"),
        "ECDH-P384": ("CRITICAL", "Shor's algorithm",          "ML-KEM-1024"),
        "ED25519":   ("HIGH",     "Shor's algorithm",          "Falcon-512"),
        "DH-2048":   ("CRITICAL", "Shor's algorithm",          "ML-KEM-768"),
        "ES256":     ("CRITICAL", "Shor's (via ECDSA)",        "ML-DSA-44"),
    }
    SAFE = {
        "AES-128":     ("MEDIUM", "Grover halves to 64-bit",   "AES-256-GCM (upgrade)"),
        "AES-256":     ("LOW",    "Grover gives 128-bit",      "Retain AES-256-GCM"),
        "AES-256-GCM": ("LOW",    "Grover gives 128-bit",      "Retain"),
        "SHA-256":     ("MEDIUM", "Grover halves to 128-bit",  "SHA-384"),
        "SHA-384":     ("LOW",    "Grover gives 192-bit",      "Retain"),
        "SHA-512":     ("LOW",    "Grover gives 256-bit",      "Retain"),
        "BCRYPT":      ("LOW",    "Not directly vulnerable",   "Argon2id"),
        "ARGON2":      ("LOW",    "Not directly vulnerable",   "Retain"),
        "ML-KEM":      ("SAFE",   "Quantum-safe (FIPS 203)",   "Already PQC"),
        "ML-DSA":      ("SAFE",   "Quantum-safe (FIPS 204)",   "Already PQC"),
        "FALCON":      ("SAFE",   "Quantum-safe (FIPS 206)",   "Already PQC"),
    }
    key = algo_name.upper().replace(" ", "-")
    if key in VULNERABLE:
        risk, threat, target = VULNERABLE[key]
        return {"algorithm": algo_name, "quantum_risk": risk,
                "broken_by": threat, "migrate_to": target, "fips_target": True}
    for k, (risk, threat, target) in SAFE.items():
        if k in key:
            return {"algorithm": algo_name, "quantum_risk": risk,
                    "broken_by": threat, "migrate_to": target, "fips_target": False}
    return {"algorithm": algo_name, "quantum_risk": "UNKNOWN",
            "broken_by": "Not assessed", "migrate_to": "Manual review required", "fips_target": False}


def run_pqc_demo() -> dict:
    """Run all four PQC algorithms and return consolidated results."""
    results = {
        "kyber_768_kem":    kyber_kem(768),
        "ml_dsa_65_sign":   dilithium_sign(b"API auth token payload", 65),
        "falcon_512_sign":  falcon_sign(b"code artifact v1.0.0", "Falcon-512"),
        "ml_dsa_44_sign":   dilithium_sign(b"JWT signing test", 44),
    }
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PQC Implementation — REAL Algorithm Test (liboqs 0.16.0)")
    print("=" * 60)

    print("\n[1] ML-KEM-768 (FIPS 203 — Kyber Key Encapsulation)")
    r = kyber_kem(768)
    for k, v in r.items():
        print(f"    {k}: {v}")

    print("\n[2] ML-DSA-65 (FIPS 204 — Dilithium Digital Signature)")
    r = dilithium_sign(b"quantum-safe API token", 65)
    for k, v in r.items():
        print(f"    {k}: {v}")

    print("\n[3] Falcon-512 (FIPS 206 — Code Signing)")
    r = falcon_sign(b"artifact hash: sha256:abc123", "Falcon-512")
    for k, v in r.items():
        print(f"    {k}: {v}")

    print("\n[4] Crypto Inventory Assessment")
    assets = ["RSA-2048", "ECDH-P256", "ECDSA-P384", "Ed25519",
              "AES-256-GCM", "SHA-256", "ML-KEM-768"]
    for a in assets:
        r = assess_algorithm(a)
        print(f"    {r['algorithm']:18s} → {r['quantum_risk']:8s}  → {r['migrate_to']}")
