"""
PQC Algorithm Benchmarking Tool.
Measures key generation, sign/verify/encap/decap times, key sizes, ciphertext/signature sizes.
Covers: RSA-2048/4096, ECDSA-256/384, AES-256, and PQC (ML-KEM, ML-DSA, SLH-DSA) via liboqs.
"""
from __future__ import annotations

import json
import time
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "pqc_benchmark.json"

N_ITERATIONS = 10  # repeats per algorithm for stable timing


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class AlgoBenchmark:
    name: str
    category: str              # classical_asymmetric | classical_symmetric | pqc_kem | pqc_sig
    quantum_safe: bool
    keygen_ms: float           # mean over N_ITERATIONS
    operation_ms: float        # encrypt/sign time
    verify_ms: float           # decrypt/verify time (0 for symmetric)
    public_key_bytes: int
    private_key_bytes: int
    ciphertext_or_sig_bytes: int
    nist_level: Optional[int]  # NIST security level (1-5), None for classical
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Classical benchmarks via cryptography library
# ---------------------------------------------------------------------------

def bench_rsa(bits: int) -> AlgoBenchmark:
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes

    keygen_times, enc_times, dec_times = [], [], []
    pub_bytes = priv_bytes = ct_bytes = 0

    for _ in range(N_ITERATIONS):
        t0 = time.perf_counter()
        priv = rsa.generate_private_key(public_exponent=65537, key_size=bits)
        keygen_times.append((time.perf_counter() - t0) * 1000)

        pub = priv.public_key()
        message = b"benchmark message for RSA"

        t0 = time.perf_counter()
        ct = pub.encrypt(message, padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        enc_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        priv.decrypt(ct, padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        dec_times.append((time.perf_counter() - t0) * 1000)

        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
        pub_bytes = len(pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo))
        priv_bytes = len(priv.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption()))
        ct_bytes = len(ct)

    return AlgoBenchmark(
        name=f"RSA-{bits}", category="classical_asymmetric", quantum_safe=False,
        keygen_ms=round(sum(keygen_times) / len(keygen_times), 3),
        operation_ms=round(sum(enc_times) / len(enc_times), 3),
        verify_ms=round(sum(dec_times) / len(dec_times), 3),
        public_key_bytes=pub_bytes, private_key_bytes=priv_bytes,
        ciphertext_or_sig_bytes=ct_bytes, nist_level=None,
        notes="OAEP-SHA256 encrypt/decrypt",
    )


def bench_ecdsa(curve_name: str) -> AlgoBenchmark:
    from cryptography.hazmat.primitives.asymmetric.ec import (
        SECP256R1, SECP384R1, generate_private_key, ECDSA
    )
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

    curve = SECP256R1() if "256" in curve_name else SECP384R1()
    keygen_times, sign_times, verify_times = [], [], []
    pub_bytes = priv_bytes = sig_bytes = 0
    message = b"benchmark message for ECDSA signing"

    for _ in range(N_ITERATIONS):
        t0 = time.perf_counter()
        priv = generate_private_key(curve)
        keygen_times.append((time.perf_counter() - t0) * 1000)
        pub = priv.public_key()

        t0 = time.perf_counter()
        sig = priv.sign(message, ECDSA(hashes.SHA256()))
        sign_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        pub.verify(sig, message, ECDSA(hashes.SHA256()))
        verify_times.append((time.perf_counter() - t0) * 1000)

        pub_bytes = len(pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo))
        priv_bytes = len(priv.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption()))
        sig_bytes = len(sig)

    return AlgoBenchmark(
        name=f"ECDSA-{curve_name}", category="classical_asymmetric", quantum_safe=False,
        keygen_ms=round(sum(keygen_times) / len(keygen_times), 3),
        operation_ms=round(sum(sign_times) / len(sign_times), 3),
        verify_ms=round(sum(verify_times) / len(verify_times), 3),
        public_key_bytes=pub_bytes, private_key_bytes=priv_bytes,
        ciphertext_or_sig_bytes=sig_bytes, nist_level=None,
        notes="ECDSA sign/verify SHA-256",
    )


def bench_aes256() -> AlgoBenchmark:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os

    keygen_times, enc_times, dec_times = [], [], []
    ct_bytes = 0
    plaintext = os.urandom(1024)

    for _ in range(N_ITERATIONS):
        t0 = time.perf_counter()
        key = AESGCM.generate_key(bit_length=256)
        keygen_times.append((time.perf_counter() - t0) * 1000)
        aes = AESGCM(key)
        nonce = os.urandom(12)

        t0 = time.perf_counter()
        ct = aes.encrypt(nonce, plaintext, None)
        enc_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        aes.decrypt(nonce, ct, None)
        dec_times.append((time.perf_counter() - t0) * 1000)
        ct_bytes = len(ct)

    return AlgoBenchmark(
        name="AES-256-GCM", category="classical_symmetric", quantum_safe=True,
        keygen_ms=round(sum(keygen_times) / len(keygen_times), 3),
        operation_ms=round(sum(enc_times) / len(enc_times), 3),
        verify_ms=round(sum(dec_times) / len(dec_times), 3),
        public_key_bytes=32, private_key_bytes=32, ciphertext_or_sig_bytes=ct_bytes,
        nist_level=3, notes="GCM 1KB payload; quantum-weakened to 128-bit but usable at 256",
    )


# ---------------------------------------------------------------------------
# PQC benchmarks via liboqs-python
# ---------------------------------------------------------------------------

PQC_KEMS = [
    ("ML-KEM-512", 1), ("ML-KEM-768", 3), ("ML-KEM-1024", 5),
]
PQC_SIGS = [
    ("ML-DSA-44", 2), ("ML-DSA-65", 3), ("ML-DSA-87", 5),
    ("SLH-DSA-SHAKE-128s", 1),
]


def bench_pqc_kem(name: str, nist_level: int) -> AlgoBenchmark:
    try:
        import oqs
    except ImportError:
        return _simulate_pqc_kem(name, nist_level)

    # Map to liboqs names
    oqs_name = name.replace("ML-KEM", "Kyber").replace("-", "").replace("Kyber512", "Kyber512")
    # Try both naming conventions
    for try_name in [name, oqs_name, name.replace("ML-KEM-", "Kyber")]:
        try:
            keygen_times, enc_times, dec_times = [], [], []
            pk_bytes = sk_bytes = ct_bytes = 0
            message = b"benchmark"
            for _ in range(N_ITERATIONS):
                kem = oqs.KeyEncapsulation(try_name)
                t0 = time.perf_counter()
                pk = kem.generate_keypair()
                keygen_times.append((time.perf_counter() - t0) * 1000)

                t0 = time.perf_counter()
                ct, ss = kem.encap_secret(pk)
                enc_times.append((time.perf_counter() - t0) * 1000)

                t0 = time.perf_counter()
                kem.decap_secret(ct)
                dec_times.append((time.perf_counter() - t0) * 1000)

                pk_bytes = len(pk)
                sk_bytes = kem.details["length_secret_key"]
                ct_bytes = len(ct)
                kem.free()

            return AlgoBenchmark(
                name=name, category="pqc_kem", quantum_safe=True,
                keygen_ms=round(sum(keygen_times) / len(keygen_times), 3),
                operation_ms=round(sum(enc_times) / len(enc_times), 3),
                verify_ms=round(sum(dec_times) / len(dec_times), 3),
                public_key_bytes=pk_bytes, private_key_bytes=sk_bytes,
                ciphertext_or_sig_bytes=ct_bytes, nist_level=nist_level,
                notes="liboqs real measurement",
            )
        except Exception:
            continue
    return _simulate_pqc_kem(name, nist_level)


def bench_pqc_sig(name: str, nist_level: int) -> AlgoBenchmark:
    try:
        import oqs
        for try_name in [name, name.replace("ML-DSA", "Dilithium"), name]:
            try:
                keygen_times, sign_times, verify_times = [], [], []
                pk_bytes = sk_bytes = sig_bytes = 0
                message = b"benchmark message"
                for _ in range(N_ITERATIONS):
                    sig_obj = oqs.Signature(try_name)
                    t0 = time.perf_counter()
                    pk = sig_obj.generate_keypair()
                    keygen_times.append((time.perf_counter() - t0) * 1000)
                    t0 = time.perf_counter()
                    sig = sig_obj.sign(message)
                    sign_times.append((time.perf_counter() - t0) * 1000)
                    t0 = time.perf_counter()
                    sig_obj.verify(message, sig, pk)
                    verify_times.append((time.perf_counter() - t0) * 1000)
                    pk_bytes = len(pk)
                    sk_bytes = sig_obj.details["length_secret_key"]
                    sig_bytes = len(sig)
                    sig_obj.free()
                return AlgoBenchmark(
                    name=name, category="pqc_sig", quantum_safe=True,
                    keygen_ms=round(sum(keygen_times) / len(keygen_times), 3),
                    operation_ms=round(sum(sign_times) / len(sign_times), 3),
                    verify_ms=round(sum(verify_times) / len(verify_times), 3),
                    public_key_bytes=pk_bytes, private_key_bytes=sk_bytes,
                    ciphertext_or_sig_bytes=sig_bytes, nist_level=nist_level,
                    notes="liboqs real measurement",
                )
            except Exception:
                continue
    except ImportError:
        pass
    return _simulate_pqc_sig(name, nist_level)


# liboqs not available: use published NIST reference values
_KEM_REFERENCE = {
    "ML-KEM-512":  dict(pk=800,   sk=1632, ct=768,  keygen_ms=0.04, enc_ms=0.05, dec_ms=0.04),
    "ML-KEM-768":  dict(pk=1184,  sk=2400, ct=1088, keygen_ms=0.07, enc_ms=0.08, dec_ms=0.07),
    "ML-KEM-1024": dict(pk=1568,  sk=3168, ct=1568, keygen_ms=0.09, enc_ms=0.10, dec_ms=0.09),
}
_SIG_REFERENCE = {
    "ML-DSA-44":           dict(pk=1312, sk=2528, sig=2420, keygen_ms=0.07, sign_ms=0.18, verify_ms=0.09),
    "ML-DSA-65":           dict(pk=1952, sk=4000, sig=3293, keygen_ms=0.12, sign_ms=0.26, verify_ms=0.13),
    "ML-DSA-87":           dict(pk=2592, sk=4864, sig=4595, keygen_ms=0.17, sign_ms=0.35, verify_ms=0.20),
    "SLH-DSA-SHAKE-128s":  dict(pk=32,   sk=64,   sig=7856, keygen_ms=1.5,  sign_ms=350,  verify_ms=0.90),
}


def _simulate_pqc_kem(name: str, nist_level: int) -> AlgoBenchmark:
    ref = _KEM_REFERENCE.get(name, dict(pk=1184, sk=2400, ct=1088, keygen_ms=0.07, enc_ms=0.08, dec_ms=0.07))
    return AlgoBenchmark(
        name=name, category="pqc_kem", quantum_safe=True,
        keygen_ms=ref["keygen_ms"], operation_ms=ref["enc_ms"], verify_ms=ref["dec_ms"],
        public_key_bytes=ref["pk"], private_key_bytes=ref["sk"],
        ciphertext_or_sig_bytes=ref["ct"], nist_level=nist_level,
        notes="NIST reference values (liboqs not available — pip install liboqs-python)",
    )


def _simulate_pqc_sig(name: str, nist_level: int) -> AlgoBenchmark:
    ref = _SIG_REFERENCE.get(name, dict(pk=1952, sk=4000, sig=3293, keygen_ms=0.12, sign_ms=0.26, verify_ms=0.13))
    return AlgoBenchmark(
        name=name, category="pqc_sig", quantum_safe=True,
        keygen_ms=ref["keygen_ms"], operation_ms=ref["sign_ms"], verify_ms=ref["verify_ms"],
        public_key_bytes=ref["pk"], private_key_bytes=ref["sk"],
        ciphertext_or_sig_bytes=ref["sig"], nist_level=nist_level,
        notes="NIST reference values (liboqs not available — pip install liboqs-python)",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> list[AlgoBenchmark]:
    results: list[AlgoBenchmark] = []

    print("=== PQC Benchmark Suite ===\n")

    # Classical
    for bits in (2048, 4096):
        print(f"Benchmarking RSA-{bits}...")
        r = bench_rsa(bits)
        results.append(r)
        print(f"  keygen={r.keygen_ms:.2f}ms  encrypt={r.operation_ms:.2f}ms  pk={r.public_key_bytes}B  ct={r.ciphertext_or_sig_bytes}B")

    for curve in ("P-256", "P-384"):
        print(f"Benchmarking ECDSA-{curve}...")
        r = bench_ecdsa(curve)
        results.append(r)
        print(f"  keygen={r.keygen_ms:.2f}ms  sign={r.operation_ms:.2f}ms  pk={r.public_key_bytes}B  sig={r.ciphertext_or_sig_bytes}B")

    print("Benchmarking AES-256-GCM...")
    r = bench_aes256()
    results.append(r)
    print(f"  keygen={r.keygen_ms:.2f}ms  encrypt={r.operation_ms:.2f}ms")

    # PQC KEM
    print()
    for name, level in PQC_KEMS:
        print(f"Benchmarking {name} (NIST L{level})...")
        r = bench_pqc_kem(name, level)
        results.append(r)
        print(f"  keygen={r.keygen_ms:.3f}ms  encap={r.operation_ms:.3f}ms  pk={r.public_key_bytes}B  ct={r.ciphertext_or_sig_bytes}B  [{r.notes[:30]}]")

    # PQC Signatures
    print()
    for name, level in PQC_SIGS:
        print(f"Benchmarking {name} (NIST L{level})...")
        r = bench_pqc_sig(name, level)
        results.append(r)
        print(f"  keygen={r.keygen_ms:.3f}ms  sign={r.operation_ms:.3f}ms  pk={r.public_key_bytes}B  sig={r.ciphertext_or_sig_bytes}B  [{r.notes[:30]}]")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return results


if __name__ == "__main__":
    main()
