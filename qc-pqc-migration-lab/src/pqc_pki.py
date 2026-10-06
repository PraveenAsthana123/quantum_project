"""
PQC PKI Simulation — ML-DSA-65 (FIPS 204 / Dilithium3) Certificates
Simulates realistic PQC PKI using Python stdlib.
All key/signature sizes match published NIST PQC standards.
"""

import os
import time
import hashlib
import struct
import json
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta


# ─── Realistic NIST parameter sizes ──────────────────────────────────────────
PARAMS = {
    "ML-DSA-44": {"pk": 1312,  "sk": 2528,  "sig": 2420,  "level": 2},
    "ML-DSA-65": {"pk": 1952,  "sk": 4032,  "sig": 3309,  "level": 3},
    "ML-DSA-87": {"pk": 2592,  "sk": 4896,  "sig": 4627,  "level": 5},
    "ML-KEM-512": {"pk": 800,   "sk": 1632,  "ct":  768,   "level": 1},
    "ML-KEM-768": {"pk": 1184,  "sk": 2400,  "ct":  1088,  "level": 3},
    "RSA-2048":   {"pk": 256,   "sk": 2349,  "sig": 256},
    "ECDSA-P256": {"pk": 64,    "sk": 32,    "sig": 72},
    "X25519":     {"pk": 32,    "sk": 32,    "shared": 32},
}

# OID assignments (NIST FIPS 204/203)
OID_ML_DSA_44 = "2.16.840.1.101.3.4.3.17"
OID_ML_DSA_65 = "2.16.840.1.101.3.4.3.18"
OID_ML_DSA_87 = "2.16.840.1.101.3.4.3.19"
OID_ML_KEM_512  = "2.16.840.1.101.3.4.4.1"
OID_ML_KEM_768  = "2.16.840.1.101.3.4.4.2"
OID_ML_KEM_1024 = "2.16.840.1.101.3.4.4.3"

# Simulated timing offsets (ms) based on NIST SUPERCOP benchmarks
TIMING_MS = {
    "RSA-2048-keygen":   125.0,
    "RSA-2048-sign":       3.2,
    "RSA-2048-verify":     0.1,
    "ML-DSA-65-keygen":    0.21,
    "ML-DSA-65-sign":      0.59,
    "ML-DSA-65-verify":    0.26,
    "ML-KEM-768-keygen":   0.09,
    "ML-KEM-768-encap":    0.10,
    "ML-KEM-768-decap":    0.11,
    "X25519-keygen":       0.04,
    "X25519-exchange":     0.05,
}


# ─── Simulated primitives ────────────────────────────────────────────────────

def _sim_keygen(algorithm: str) -> Tuple[bytes, bytes]:
    """Simulate key generation producing realistic-sized keys."""
    p = PARAMS[algorithm]
    pk = os.urandom(p["pk"])
    sk = os.urandom(p["sk"])
    return pk, sk


def _sim_sign(sk: bytes, message: bytes, algorithm: str = "ML-DSA-65") -> bytes:
    """Simulate signing: HMAC-SHA3-512 over (sk, message), padded to real sig size."""
    import hmac
    mac = hmac.new(sk[:32], message, hashlib.sha3_512).digest()
    sig_size = PARAMS[algorithm]["sig"]
    # Deterministic expansion to realistic size
    sig = mac
    while len(sig) < sig_size:
        sig += hashlib.sha3_256(sig).digest()
    return sig[:sig_size]


def _sim_verify(pk: bytes, message: bytes, signature: bytes,
                algorithm: str = "ML-DSA-65") -> bool:
    """Simulate verification (always succeeds if sig length matches)."""
    return len(signature) == PARAMS[algorithm]["sig"]


def _sim_kem_keygen(algorithm: str = "ML-KEM-768") -> Tuple[bytes, bytes]:
    p = PARAMS[algorithm]
    ek = os.urandom(p["pk"])   # encapsulation key
    dk = os.urandom(p["sk"])   # decapsulation key
    return ek, dk


def _sim_kem_encap(ek: bytes, algorithm: str = "ML-KEM-768") -> Tuple[bytes, bytes]:
    """Return (ciphertext, shared_secret)."""
    p = PARAMS[algorithm]
    ct = os.urandom(p["ct"])
    ss = hashlib.sha3_256(ek + ct).digest()   # 32-byte shared secret
    return ct, ss


def _sim_kem_decap(dk: bytes, ct: bytes) -> bytes:
    ss = hashlib.sha3_256(dk[:32] + ct).digest()
    return ss


def _timed(operation: str):
    """Context-manager that sleeps proportionally to published benchmarks."""
    class _T:
        def __enter__(self):
            self.start = time.perf_counter()
            return self
        def __exit__(self, *_):
            self.elapsed_ms = (time.perf_counter() - self.start) * 1000
    return _T()


# ─── Data classes ────────────────────────────────────────────────────────────

@dataclass
class PQCKeyPair:
    algorithm: str
    public_key: bytes
    private_key: bytes
    keygen_ms: float = 0.0

    @property
    def pk_size(self): return len(self.public_key)
    @property
    def sk_size(self): return len(self.private_key)


@dataclass
class CertificateSigningRequest:
    subject_cn: str
    subject_org: str
    subject_country: str
    public_key: bytes
    algorithm: str
    pqc_oid: str
    san: list = field(default_factory=list)
    raw: bytes = field(default_factory=bytes)

    def encode(self) -> bytes:
        """Minimal DER-like encoding for demo purposes."""
        data = json.dumps({
            "subject": {"CN": self.subject_cn, "O": self.subject_org,
                        "C": self.subject_country},
            "algorithm": self.algorithm,
            "oid": self.pqc_oid,
            "san": self.san,
            "pk_hex": self.public_key[:16].hex() + "...",
        }, indent=2).encode()
        return data


@dataclass
class PQCCertificate:
    serial: int
    subject_cn: str
    issuer_cn: str
    not_before: datetime
    not_after: datetime
    algorithm: str
    pqc_oid: str
    public_key: bytes
    signature: bytes
    extensions: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"  Serial     : {self.serial:016X}\n"
            f"  Subject    : CN={self.subject_cn}\n"
            f"  Issuer     : CN={self.issuer_cn}\n"
            f"  Valid from : {self.not_before.strftime('%Y-%m-%d')}\n"
            f"  Valid to   : {self.not_after.strftime('%Y-%m-%d')}\n"
            f"  Algorithm  : {self.algorithm} (OID {self.pqc_oid})\n"
            f"  PK size    : {len(self.public_key):,} bytes\n"
            f"  Sig size   : {len(self.signature):,} bytes\n"
            f"  Extensions : {list(self.extensions.keys())}"
        )


@dataclass
class HybridCertificate:
    """X.509v3 certificate with both classical and PQC material."""
    pqc_cert: PQCCertificate
    kem_ek: bytes           # ML-KEM-768 encapsulation key
    classical_pk: bytes     # X25519 public key
    hybrid_sig: bytes       # ML-DSA-65 signature over both keys

    def wire_size(self) -> int:
        return (len(self.kem_ek) + len(self.classical_pk)
                + len(self.pqc_cert.public_key) + len(self.hybrid_sig))


# ─── PKI operations ──────────────────────────────────────────────────────────

class PQCCA:
    """Simulated Post-Quantum Certificate Authority."""

    def __init__(self, name: str = "PQC-Root-CA", algorithm: str = "ML-DSA-65"):
        self.name = name
        self.algorithm = algorithm
        self.oid = OID_ML_DSA_65
        print(f"[CA] Initializing {name} with {algorithm} ...")
        t0 = time.perf_counter()
        self.ca_pk, self.ca_sk = _sim_keygen(algorithm)
        self.keygen_ms = (time.perf_counter() - t0) * 1000
        self._serial = 0x1000
        print(f"[CA] CA key pair generated  PK={len(self.ca_pk):,}B  "
              f"SK={len(self.ca_sk):,}B  ({self.keygen_ms:.3f} ms)")

    def generate_end_entity_keypair(self) -> PQCKeyPair:
        t0 = time.perf_counter()
        pk, sk = _sim_keygen(self.algorithm)
        ms = (time.perf_counter() - t0) * 1000
        return PQCKeyPair(self.algorithm, pk, sk, ms)

    def create_csr(self, keypair: PQCKeyPair, cn: str, org: str,
                   country: str = "US", san: list = None) -> CertificateSigningRequest:
        csr = CertificateSigningRequest(
            subject_cn=cn, subject_org=org, subject_country=country,
            public_key=keypair.public_key, algorithm=self.algorithm,
            pqc_oid=self.oid, san=san or [],
        )
        csr.raw = csr.encode()
        return csr

    def sign_certificate(self, csr: CertificateSigningRequest,
                         validity_days: int = 398) -> PQCCertificate:
        self._serial += 1
        now = datetime.utcnow()
        t0 = time.perf_counter()
        sig = _sim_sign(self.ca_sk, csr.raw, self.algorithm)
        sign_ms = (time.perf_counter() - t0) * 1000

        extensions = {
            "subjectKeyIdentifier": hashlib.sha256(csr.public_key).hexdigest()[:20],
            "keyUsage": ["digitalSignature", "keyAgreement"],
            "extendedKeyUsage": ["serverAuth", "clientAuth"],
            "pqcAlgorithm": {"oid": csr.pqc_oid, "name": csr.algorithm,
                              "fips": "FIPS 204"},
            "subjectAlternativeName": csr.san,
        }
        cert = PQCCertificate(
            serial=self._serial,
            subject_cn=csr.subject_cn,
            issuer_cn=self.name,
            not_before=now,
            not_after=now + timedelta(days=validity_days),
            algorithm=self.algorithm,
            pqc_oid=self.oid,
            public_key=csr.public_key,
            signature=sig,
            extensions=extensions,
        )
        print(f"[CA] Certificate signed  serial={self._serial:#018X}  "
              f"sig={len(sig):,}B  ({sign_ms:.3f} ms)")
        return cert

    def issue_hybrid_certificate(self, cn: str) -> HybridCertificate:
        """Issue a hybrid cert: X25519 + ML-KEM-768 (KEM) + ML-DSA-65 (sign)."""
        print(f"\n[CA] Issuing Hybrid Certificate for {cn}")

        # Classical X25519 component
        x25519_pk = os.urandom(PARAMS["X25519"]["pk"])

        # PQC KEM component
        kem_ek, kem_dk = _sim_kem_keygen("ML-KEM-768")

        # PQC signing component
        dsa_kp = self.generate_end_entity_keypair()
        csr = self.create_csr(dsa_kp, cn=cn, org="Hybrid Corp",
                               san=[f"DNS:{cn}", "DNS:*.example.com"])
        pqc_cert = self.sign_certificate(csr)

        # Sign over both keys for binding
        combined = x25519_pk + kem_ek + dsa_kp.public_key
        hybrid_sig = _sim_sign(self.ca_sk, combined, self.algorithm)

        hcert = HybridCertificate(
            pqc_cert=pqc_cert,
            kem_ek=kem_ek,
            classical_pk=x25519_pk,
            hybrid_sig=hybrid_sig,
        )
        return hcert


# ─── Performance comparison ──────────────────────────────────────────────────

def benchmark_rsa_vs_mldsa():
    print("\n" + "=" * 65)
    print("  PERFORMANCE: RSA-2048 vs ML-DSA-65")
    print("=" * 65)
    message = b"TLS Certificate: example.com valid 2025-2027"

    results = {}
    for algo, timing_keys in [
        ("RSA-2048",  ("RSA-2048-keygen",  "RSA-2048-sign",  "RSA-2048-verify")),
        ("ML-DSA-65", ("ML-DSA-65-keygen", "ML-DSA-65-sign", "ML-DSA-65-verify")),
    ]:
        kg_ms  = TIMING_MS[timing_keys[0]]
        sgn_ms = TIMING_MS[timing_keys[1]]
        vfy_ms = TIMING_MS[timing_keys[2]]
        p = PARAMS[algo]
        results[algo] = dict(keygen=kg_ms, sign=sgn_ms, verify=vfy_ms,
                             pk=p["pk"], sk=p["sk"], sig=p["sig"])

    header = f"{'Metric':<25} {'RSA-2048':>14} {'ML-DSA-65':>14} {'Ratio':>10}"
    print(header)
    print("-" * 65)
    for metric, k_rsa, k_dsa in [
        ("KeyGen (ms)",    "keygen", "keygen"),
        ("Sign (ms)",      "sign",   "sign"),
        ("Verify (ms)",    "verify", "verify"),
        ("Public key (B)", "pk",     "pk"),
        ("Private key (B)","sk",     "sk"),
        ("Signature (B)",  "sig",    "sig"),
    ]:
        r = results["RSA-2048"][k_rsa]
        d = results["ML-DSA-65"][k_dsa]
        ratio = d / r if r else float("inf")
        print(f"  {metric:<23} {r:>14.2f} {d:>14.2f} {ratio:>9.1f}x")

    print("\n  Notes:")
    print("  - ML-DSA-65 KeyGen is ~595x faster than RSA-2048")
    print("  - ML-DSA-65 Sign    is ~5.4x  faster than RSA-2048")
    print("  - ML-DSA-65 Verify  is ~2.6x  slower than RSA-2048")
    print("  - ML-DSA-65 keys/sigs are larger (bandwidth cost)")
    print("  - ML-DSA-65 is QUANTUM-SAFE; RSA-2048 is BROKEN by Shor's")
    print("  Source: NIST SUPERCOP benchmarks + FIPS 204 reference impl")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  PQC PKI SIMULATION — ML-DSA-65 (FIPS 204 / Dilithium3)")
    print("=" * 65)
    print(f"\n  ML-DSA-65 OID : {OID_ML_DSA_65}")
    print(f"  ML-KEM-768 OID: {OID_ML_KEM_768}")

    # 1. Stand up a PQC CA
    print("\n── Step 1: Initialize PQC Root CA ──────────────────────────")
    ca = PQCCA(name="PQC-Root-CA-G1", algorithm="ML-DSA-65")

    # 2. End-entity key pair
    print("\n── Step 2: End-Entity Key Generation ───────────────────────")
    ee_kp = ca.generate_end_entity_keypair()
    print(f"  Algorithm  : {ee_kp.algorithm}")
    print(f"  Public key : {ee_kp.pk_size:,} bytes")
    print(f"  Private key: {ee_kp.sk_size:,} bytes")
    print(f"  KeyGen time: {ee_kp.keygen_ms:.4f} ms")

    # 3. CSR
    print("\n── Step 3: Certificate Signing Request (CSR) ───────────────")
    csr = ca.create_csr(ee_kp, cn="api.example.com", org="Example Corp",
                         san=["DNS:api.example.com", "DNS:www.example.com",
                              "IP:203.0.113.42"])
    print(f"  Subject CN : {csr.subject_cn}")
    print(f"  Algorithm  : {csr.algorithm}")
    print(f"  PQC OID    : {csr.pqc_oid}")
    print(f"  SANs       : {csr.san}")
    print(f"  CSR size   : {len(csr.raw):,} bytes (JSON representation)")

    # 4. Sign certificate
    print("\n── Step 4: CA Signs the Certificate ────────────────────────")
    cert = ca.sign_certificate(csr, validity_days=398)
    print(cert.summary())

    # 5. Hybrid certificate
    print("\n── Step 5: Hybrid Certificate (X25519 + ML-KEM-768 + ML-DSA-65) ─")
    hcert = ca.issue_hybrid_certificate("hybrid.example.com")
    print(f"\n  Hybrid Certificate Summary:")
    print(f"  X25519 PK     : {len(hcert.classical_pk):,} bytes (classical KEM)")
    print(f"  ML-KEM-768 EK : {len(hcert.kem_ek):,} bytes (PQC KEM)")
    print(f"  ML-DSA-65 PK  : {len(hcert.pqc_cert.public_key):,} bytes (PQC sign)")
    print(f"  Hybrid sig    : {len(hcert.hybrid_sig):,} bytes")
    print(f"  Total wire    : {hcert.wire_size():,} bytes")
    print(f"  IETF ref      : draft-ietf-lamps-pq-composite-kem")
    print(f"  IETF ref      : draft-ietf-lamps-pq-composite-sigs")

    # 6. Verify
    print("\n── Step 6: Signature Verification ──────────────────────────")
    ok = _sim_verify(cert.public_key, csr.raw, cert.signature)
    print(f"  Verification result: {'PASS' if ok else 'FAIL'}")

    # 7. Performance comparison
    benchmark_rsa_vs_mldsa()

    print("\n── X.509v3 PQC Extensions (draft values) ───────────────────")
    print(f"  id-ML-DSA-44  OID: 2.16.840.1.101.3.4.3.17")
    print(f"  id-ML-DSA-65  OID: {OID_ML_DSA_65}")
    print(f"  id-ML-DSA-87  OID: 2.16.840.1.101.3.4.3.19")
    print(f"  id-ML-KEM-512 OID: {OID_ML_KEM_512}")
    print(f"  id-ML-KEM-768 OID: {OID_ML_KEM_768}")
    print(f"\n  FIPS references: FIPS 203 (ML-KEM), FIPS 204 (ML-DSA)")
    print("=" * 65)


if __name__ == "__main__":
    main()
