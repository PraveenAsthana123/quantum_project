"""
Crypto-Agility Framework — algorithm abstraction and rapid replacement
=====================================================================
Version : 1.0
Date    : 2026-10-06
Standard: NIST SP 800-175B, CNSA 2.0 Suite, IETF RFC 9382 (crypto agility)
Purpose : Enable organizations to swap cryptographic algorithms without
          rewriting applications; core enterprise PQC migration enabler
"""
from __future__ import annotations

import json
import time
import hashlib
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ─── Enumerations ─────────────────────────────────────────────────────────────

class AlgorithmStatus(str, Enum):
    ACTIVE           = "ACTIVE"
    DEPRECATED       = "DEPRECATED"
    PHASED_OUT       = "PHASED_OUT"
    QUANTUM_VULNERABLE = "QUANTUM_VULNERABLE"
    QUANTUM_SAFE     = "QUANTUM_SAFE"
    EXPERIMENTAL     = "EXPERIMENTAL"


class AlgorithmFamily(str, Enum):
    RSA       = "RSA"
    ECC       = "ECC"
    DH        = "DH"
    AES       = "AES"
    SHA       = "SHA"
    ML_KEM    = "ML_KEM"
    ML_DSA    = "ML_DSA"
    SLH_DSA   = "SLH_DSA"
    BIKE      = "BIKE"
    MCELIECE  = "MCELIECE"
    QRNG      = "QRNG"


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class CryptoAlgorithm:
    name: str
    family: AlgorithmFamily
    key_size_bits: int
    status: AlgorithmStatus
    quantum_vulnerable: bool
    cnsa2_approved: bool
    nist_standard: str                   # e.g. "FIPS 203", "SP 800-131A"
    performance_score: float             # 0.0 (slowest) – 10.0 (fastest)
    migration_priority: int              # 1 = migrate immediately, 5 = low urgency
    # Optional extended fields
    classical_security_bits: int = 0
    pq_security_bits: int = 0
    quantum_attack: str = "N/A"          # e.g. "Shor's", "Grover's", "None"
    cnsa2_deadline: str = "N/A"          # e.g. "2030-01-01"
    use_cases: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class MigrationPlan:
    from_algo: str
    to_algo: str
    system_count: int
    phases: List[Dict[str, Any]]
    estimated_days: int
    effort_person_days: int
    risk_level: str                      # LOW / MEDIUM / HIGH / CRITICAL
    rollback_path: str
    testing_requirements: List[str]
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


# ─── Algorithm registry (30+ entries) ────────────────────────────────────────

_ALGORITHM_REGISTRY_RAW: List[Dict[str, Any]] = [
    # ── RSA family ────────────────────────────────────────────────────────────
    {
        "name": "RSA-1024",
        "family": AlgorithmFamily.RSA,
        "key_size_bits": 1024,
        "status": AlgorithmStatus.PHASED_OUT,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-131A Rev.2 (disallowed)",
        "performance_score": 7.5,
        "migration_priority": 1,
        "classical_security_bits": 80,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (factoring)",
        "cnsa2_deadline": "2025-01-01",
        "use_cases": ["Legacy TLS", "Legacy code signing"],
        "notes": "Classically weak; immediately replace.",
    },
    {
        "name": "RSA-2048",
        "family": AlgorithmFamily.RSA,
        "key_size_bits": 2048,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-131A Rev.2 (disallowed after 2030)",
        "performance_score": 6.5,
        "migration_priority": 1,
        "classical_security_bits": 112,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (factoring)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["TLS certificates", "Code signing", "S/MIME"],
        "notes": "Widely deployed; CNSA 2.0 deadline 2030.",
    },
    {
        "name": "RSA-3072",
        "family": AlgorithmFamily.RSA,
        "key_size_bits": 3072,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-131A Rev.2",
        "performance_score": 5.5,
        "migration_priority": 2,
        "classical_security_bits": 128,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (factoring)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["High-assurance TLS", "CA certificates"],
        "notes": "Stronger classical but equally broken by Shor's.",
    },
    {
        "name": "RSA-4096",
        "family": AlgorithmFamily.RSA,
        "key_size_bits": 4096,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-131A Rev.2",
        "performance_score": 4.5,
        "migration_priority": 2,
        "classical_security_bits": 140,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (factoring)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["Root CA keys", "Long-lived signing keys"],
        "notes": "Performance penalty significant; no PQ benefit over RSA-2048.",
    },
    # ── ECC family ────────────────────────────────────────────────────────────
    {
        "name": "ECDSA-P256",
        "family": AlgorithmFamily.ECC,
        "key_size_bits": 256,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "FIPS 186-5",
        "performance_score": 8.5,
        "migration_priority": 1,
        "classical_security_bits": 128,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (discrete log)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["TLS 1.3 auth", "JWT signing", "DNSSEC"],
        "notes": "Ubiquitous; requires coordinated replacement across PKI.",
    },
    {
        "name": "ECDSA-P384",
        "family": AlgorithmFamily.ECC,
        "key_size_bits": 384,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "FIPS 186-5",
        "performance_score": 7.8,
        "migration_priority": 2,
        "classical_security_bits": 192,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (discrete log)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["Suite B classified comms", "High-assurance signing"],
        "notes": "Used in NSA Suite B; CNSA 1.0 approved, CNSA 2.0 deprecated.",
    },
    {
        "name": "X25519",
        "family": AlgorithmFamily.ECC,
        "key_size_bits": 255,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "RFC 7748",
        "performance_score": 9.2,
        "migration_priority": 1,
        "classical_security_bits": 128,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (ECDH discrete log)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["TLS 1.3 key exchange", "Signal protocol", "SSH"],
        "notes": "Fastest ECDH option; pair with ML-KEM-768 for hybrid.",
    },
    {
        "name": "ECDH-P256",
        "family": AlgorithmFamily.ECC,
        "key_size_bits": 256,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-56A",
        "performance_score": 8.2,
        "migration_priority": 1,
        "classical_security_bits": 128,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (ECDH discrete log)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["TLS key exchange", "S/MIME key wrap"],
        "notes": "Replace with ML-KEM or hybrid X25519+ML-KEM-768.",
    },
    # ── DH family ─────────────────────────────────────────────────────────────
    {
        "name": "DH-2048",
        "family": AlgorithmFamily.DH,
        "key_size_bits": 2048,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-56A Rev.3",
        "performance_score": 5.0,
        "migration_priority": 1,
        "classical_security_bits": 112,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (discrete log)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["IKEv2", "TLS 1.2 DHE", "VPN"],
        "notes": "Static DH groups increase HNDL risk; replace immediately.",
    },
    {
        "name": "DH-3072",
        "family": AlgorithmFamily.DH,
        "key_size_bits": 3072,
        "status": AlgorithmStatus.QUANTUM_VULNERABLE,
        "quantum_vulnerable": True,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-56A Rev.3",
        "performance_score": 4.2,
        "migration_priority": 2,
        "classical_security_bits": 128,
        "pq_security_bits": 0,
        "quantum_attack": "Shor's (discrete log)",
        "cnsa2_deadline": "2030-01-01",
        "use_cases": ["IKEv2 high-assurance", "TLS DHE"],
        "notes": "Stronger classically but still Shor's vulnerable.",
    },
    # ── AES family ────────────────────────────────────────────────────────────
    {
        "name": "AES-128",
        "family": AlgorithmFamily.AES,
        "key_size_bits": 128,
        "status": AlgorithmStatus.DEPRECATED,
        "quantum_vulnerable": False,
        "cnsa2_approved": False,
        "nist_standard": "FIPS 197",
        "performance_score": 9.8,
        "migration_priority": 4,
        "classical_security_bits": 128,
        "pq_security_bits": 64,
        "quantum_attack": "Grover's (halves effective key length)",
        "cnsa2_deadline": "N/A",
        "use_cases": ["TLS record layer", "Disk encryption"],
        "notes": "Grover's reduces to 64-bit PQ security; CNSA 2.0 requires AES-256.",
    },
    {
        "name": "AES-192",
        "family": AlgorithmFamily.AES,
        "key_size_bits": 192,
        "status": AlgorithmStatus.ACTIVE,
        "quantum_vulnerable": False,
        "cnsa2_approved": False,
        "nist_standard": "FIPS 197",
        "performance_score": 9.5,
        "migration_priority": 3,
        "classical_security_bits": 192,
        "pq_security_bits": 96,
        "quantum_attack": "Grover's (halves effective key length)",
        "cnsa2_deadline": "N/A",
        "use_cases": ["Interim use"],
        "notes": "Acceptable but CNSA 2.0 prefers AES-256.",
    },
    {
        "name": "AES-256",
        "family": AlgorithmFamily.AES,
        "key_size_bits": 256,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 197 / CNSA 2.0",
        "performance_score": 9.3,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 128,
        "quantum_attack": "Grover's (128-bit PQ residual — acceptable)",
        "cnsa2_deadline": "N/A — already approved",
        "use_cases": ["All symmetric encryption", "TLS 1.3", "Disk encryption", "HSM bulk"],
        "notes": "CNSA 2.0 mandatory for symmetric. AES-256-GCM preferred mode.",
    },
    # ── SHA family ────────────────────────────────────────────────────────────
    {
        "name": "SHA-1",
        "family": AlgorithmFamily.SHA,
        "key_size_bits": 160,
        "status": AlgorithmStatus.PHASED_OUT,
        "quantum_vulnerable": False,
        "cnsa2_approved": False,
        "nist_standard": "SP 800-131A Rev.2 (disallowed)",
        "performance_score": 9.0,
        "migration_priority": 1,
        "classical_security_bits": 80,
        "pq_security_bits": 40,
        "quantum_attack": "Grover's + classical collision attacks",
        "cnsa2_deadline": "2025-01-01",
        "use_cases": ["Legacy code signing (disallowed)"],
        "notes": "Classically broken (SHAttered). Remove from all code paths.",
    },
    {
        "name": "SHA-256",
        "family": AlgorithmFamily.SHA,
        "key_size_bits": 256,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 180-4 / CNSA 2.0",
        "performance_score": 9.5,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 128,
        "quantum_attack": "Grover's (128-bit PQ residual)",
        "cnsa2_deadline": "N/A — already approved",
        "use_cases": ["Certificate hashing", "HMAC", "General integrity"],
        "notes": "CNSA 2.0 approved. Acceptable for all standard workloads.",
    },
    {
        "name": "SHA-384",
        "family": AlgorithmFamily.SHA,
        "key_size_bits": 384,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 180-4 / CNSA 2.0",
        "performance_score": 9.2,
        "migration_priority": 5,
        "classical_security_bits": 384,
        "pq_security_bits": 192,
        "quantum_attack": "Grover's (192-bit PQ residual — above threshold)",
        "cnsa2_deadline": "N/A — already approved",
        "use_cases": ["High-assurance hashing", "TLS 1.3 PRF", "ML-DSA internal"],
        "notes": "Preferred over SHA-256 for long-lifetime data.",
    },
    {
        "name": "SHA3-256",
        "family": AlgorithmFamily.SHA,
        "key_size_bits": 256,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 202",
        "performance_score": 8.8,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 128,
        "quantum_attack": "Grover's (128-bit PQ residual)",
        "cnsa2_deadline": "N/A — already approved",
        "use_cases": ["SLH-DSA internal", "Blockchain", "ZKP"],
        "notes": "Keccak-based; distinct from SHA-2 family; used inside PQC schemes.",
    },
    # ── ML-KEM (CRYSTALS-Kyber) ───────────────────────────────────────────────
    {
        "name": "ML-KEM-512",
        "family": AlgorithmFamily.ML_KEM,
        "key_size_bits": 1632,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 203",
        "performance_score": 9.0,
        "migration_priority": 5,
        "classical_security_bits": 128,
        "pq_security_bits": 128,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["Constrained IoT key exchange", "TLS 1.3 hybrid"],
        "notes": "Security category 1. Fastest ML-KEM. Use when bandwidth is limited.",
    },
    {
        "name": "ML-KEM-768",
        "family": AlgorithmFamily.ML_KEM,
        "key_size_bits": 2400,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 203",
        "performance_score": 8.7,
        "migration_priority": 5,
        "classical_security_bits": 192,
        "pq_security_bits": 192,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["TLS 1.3 (X25519+ML-KEM-768 hybrid)", "VPN IKEv2", "Signal"],
        "notes": "Security category 3. Recommended default for enterprise TLS.",
    },
    {
        "name": "ML-KEM-1024",
        "family": AlgorithmFamily.ML_KEM,
        "key_size_bits": 3168,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 203",
        "performance_score": 8.3,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 256,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["High-assurance government KEX", "Long-lifetime secrets"],
        "notes": "Security category 5. Use for SECRET/TOP SECRET traffic.",
    },
    # ── ML-DSA (CRYSTALS-Dilithium) ───────────────────────────────────────────
    {
        "name": "ML-DSA-44",
        "family": AlgorithmFamily.ML_DSA,
        "key_size_bits": 1312,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 204",
        "performance_score": 8.9,
        "migration_priority": 5,
        "classical_security_bits": 128,
        "pq_security_bits": 128,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["Code signing", "TLS certificate auth", "JWT"],
        "notes": "Security category 2. Recommended default for signatures.",
    },
    {
        "name": "ML-DSA-65",
        "family": AlgorithmFamily.ML_DSA,
        "key_size_bits": 1952,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 204",
        "performance_score": 8.5,
        "migration_priority": 5,
        "classical_security_bits": 192,
        "pq_security_bits": 192,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["CA certificates", "DNSSEC signing", "High-assurance auth"],
        "notes": "Security category 3. Balanced for most enterprise use cases.",
    },
    {
        "name": "ML-DSA-87",
        "family": AlgorithmFamily.ML_DSA,
        "key_size_bits": 2592,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 204",
        "performance_score": 8.1,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 256,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["Root CA keys", "Long-lifetime government signing"],
        "notes": "Security category 5. Highest ML-DSA security level.",
    },
    # ── SLH-DSA (SPHINCS+) ────────────────────────────────────────────────────
    {
        "name": "SLH-DSA-128f",
        "family": AlgorithmFamily.SLH_DSA,
        "key_size_bits": 32,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 205",
        "performance_score": 6.5,
        "migration_priority": 5,
        "classical_security_bits": 128,
        "pq_security_bits": 128,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["Offline root CA", "Firmware signing", "Long-lifetime archives"],
        "notes": "Hash-based; minimal security assumptions. Fast verification, slow signing.",
    },
    {
        "name": "SLH-DSA-192f",
        "family": AlgorithmFamily.SLH_DSA,
        "key_size_bits": 48,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 205",
        "performance_score": 6.0,
        "migration_priority": 5,
        "classical_security_bits": 192,
        "pq_security_bits": 192,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["High-value firmware", "Government document signing"],
        "notes": "Security category 3. Larger signatures (35 KB) than ML-DSA.",
    },
    {
        "name": "SLH-DSA-256f",
        "family": AlgorithmFamily.SLH_DSA,
        "key_size_bits": 64,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "FIPS 205",
        "performance_score": 5.5,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 256,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — target algorithm",
        "use_cases": ["Long-lived secret signing", "Nuclear/defense command auth"],
        "notes": "Security category 5. Highest assurance hash-based signature.",
    },
    # ── BIKE ──────────────────────────────────────────────────────────────────
    {
        "name": "BIKE-L1",
        "family": AlgorithmFamily.BIKE,
        "key_size_bits": 1271,
        "status": AlgorithmStatus.EXPERIMENTAL,
        "quantum_vulnerable": False,
        "cnsa2_approved": False,
        "nist_standard": "NIST PQC Round 4 (not yet standardized)",
        "performance_score": 7.8,
        "migration_priority": 5,
        "classical_security_bits": 128,
        "pq_security_bits": 128,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — not CNSA 2.0 approved",
        "use_cases": ["Research / constrained environments"],
        "notes": "Code-based KEM. Smaller keys than McEliece. Monitor NIST Round 4 outcome.",
    },
    {
        "name": "BIKE-L3",
        "family": AlgorithmFamily.BIKE,
        "key_size_bits": 1541,
        "status": AlgorithmStatus.EXPERIMENTAL,
        "quantum_vulnerable": False,
        "cnsa2_approved": False,
        "nist_standard": "NIST PQC Round 4 (not yet standardized)",
        "performance_score": 7.3,
        "migration_priority": 5,
        "classical_security_bits": 192,
        "pq_security_bits": 192,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — not CNSA 2.0 approved",
        "use_cases": ["Research / high-assurance experimental"],
        "notes": "Code-based KEM, security level 3. Experimental only.",
    },
    # ── Classic McEliece ──────────────────────────────────────────────────────
    {
        "name": "Classic-McEliece-348864",
        "family": AlgorithmFamily.MCELIECE,
        "key_size_bits": 261120,
        "status": AlgorithmStatus.EXPERIMENTAL,
        "quantum_vulnerable": False,
        "cnsa2_approved": False,
        "nist_standard": "NIST PQC Round 4 (not yet standardized)",
        "performance_score": 3.5,
        "migration_priority": 5,
        "classical_security_bits": 128,
        "pq_security_bits": 128,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — not CNSA 2.0 approved",
        "use_cases": ["Research, long-lifetime key encapsulation"],
        "notes": "261 KB public key makes it impractical for TLS but strong for offline use.",
    },
    {
        "name": "Classic-McEliece-6960119",
        "family": AlgorithmFamily.MCELIECE,
        "key_size_bits": 1044992,
        "status": AlgorithmStatus.EXPERIMENTAL,
        "quantum_vulnerable": False,
        "cnsa2_approved": False,
        "nist_standard": "NIST PQC Round 4 (not yet standardized)",
        "performance_score": 2.5,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 256,
        "quantum_attack": "None known",
        "cnsa2_deadline": "N/A — not CNSA 2.0 approved",
        "use_cases": ["Air-gapped, offline ultra-high-security"],
        "notes": "1 MB public key. Purely experimental; bandwidth-prohibitive.",
    },
    # ── QRNG ──────────────────────────────────────────────────────────────────
    {
        "name": "QRNG-Hardware",
        "family": AlgorithmFamily.QRNG,
        "key_size_bits": 0,
        "status": AlgorithmStatus.QUANTUM_SAFE,
        "quantum_vulnerable": False,
        "cnsa2_approved": True,
        "nist_standard": "NIST SP 800-90C (draft)",
        "performance_score": 9.9,
        "migration_priority": 5,
        "classical_security_bits": 256,
        "pq_security_bits": 256,
        "quantum_attack": "None — entropy source, not cipher",
        "cnsa2_deadline": "N/A — recommended",
        "use_cases": ["Seed for all KDFs", "Key material generation", "Nonce generation"],
        "notes": "True random; photon-based or vacuum-fluctuation based. ID Quantique, QuintessenceLabs.",
    },
]

# Build typed CryptoAlgorithm objects from raw dicts
_BUILTIN_ALGORITHMS: List[CryptoAlgorithm] = [
    CryptoAlgorithm(**{k: v for k, v in raw.items()}) for raw in _ALGORITHM_REGISTRY_RAW
]

# Migration compatibility table: (classical, pq) → (compatible:bool, notes:str)
_HYBRID_COMPATIBILITY: Dict[Tuple[str, str], Tuple[bool, str]] = {
    ("X25519",    "ML-KEM-768"):  (True,  "RFC 9370 X25519Kyber768Draft00; supported in TLS 1.3 (IETF draft)"),
    ("X25519",    "ML-KEM-512"):  (True,  "Hybrid X25519+ML-KEM-512; lower security level — prefer ML-KEM-768"),
    ("X25519",    "ML-KEM-1024"): (True,  "X25519+ML-KEM-1024 hybrid; used for long-lifetime secrets"),
    ("ECDH-P256", "ML-KEM-768"):  (True,  "P256+Kyber768 hybrid; supported in OQS-OpenSSL provider"),
    ("ECDH-P256", "ML-KEM-512"):  (True,  "P256+ML-KEM-512; constrained TLS 1.3 hybrid"),
    ("DH-2048",   "ML-KEM-768"):  (False, "DH-2048 is quantum-vulnerable; replace DH leg with X25519 first"),
    ("RSA-2048",  "ML-DSA-44"):   (True,  "RSA-2048 classical + ML-DSA-44 PQ in dual-sign PKI transitions"),
    ("ECDSA-P256","ML-DSA-44"):   (True,  "P256+Dilithium2 dual-sign; used in x509 hybrid cert profiles"),
    ("ECDSA-P384","ML-DSA-65"):   (True,  "P384+Dilithium3 dual-sign; balanced security levels"),
    ("AES-256",   "ML-KEM-768"):  (True,  "AES-256 data encryption + ML-KEM-768 KEX; standard pattern"),
    ("AES-128",   "ML-KEM-512"):  (False, "AES-128 reduces symmetric PQ to 64 bits — weaker than ML-KEM-512"),
    ("SHA-256",   "ML-DSA-44"):   (True,  "SHA-256 hashing + ML-DSA-44 signing; matched 128-bit security"),
    ("SHA-384",   "ML-DSA-65"):   (True,  "SHA-384 + ML-DSA-65; matched 192-bit security levels"),
}

# Policy-as-code: use-case → required algorithm families
_USE_CASE_POLICY: Dict[str, Dict[str, Any]] = {
    "tls13_key_exchange": {
        "allowed_families": [AlgorithmFamily.ML_KEM],
        "hybrid_required_until": "2030-01-01",
        "cnsa2_deadline": "2030-01-01",
        "notes": "CNSA 2.0 mandates ML-KEM by 2030; hybrid with X25519 acceptable until then.",
    },
    "code_signing": {
        "allowed_families": [AlgorithmFamily.ML_DSA, AlgorithmFamily.SLH_DSA],
        "hybrid_required_until": "2028-01-01",
        "cnsa2_deadline": "2028-01-01",
        "notes": "Software supply chain requires ML-DSA-44 minimum; ML-DSA-65 for CA certs.",
    },
    "bulk_encryption": {
        "allowed_families": [AlgorithmFamily.AES],
        "min_key_size": 256,
        "cnsa2_deadline": "N/A — AES-256 already CNSA 2.0 approved",
        "notes": "AES-256-GCM mandatory; AES-128 must be migrated.",
    },
    "pki_ca_signing": {
        "allowed_families": [AlgorithmFamily.ML_DSA, AlgorithmFamily.SLH_DSA],
        "hybrid_required_until": "2030-01-01",
        "cnsa2_deadline": "2030-01-01",
        "notes": "Root CA must use ML-DSA-87 or SLH-DSA-256f for long-lived keys.",
    },
    "ike_vpn": {
        "allowed_families": [AlgorithmFamily.ML_KEM],
        "hybrid_required_until": "2030-01-01",
        "cnsa2_deadline": "2030-01-01",
        "notes": "IKEv2 ML-KEM-768 KEM; StrongSwan 6.0+ supports natively.",
    },
    "document_signing": {
        "allowed_families": [AlgorithmFamily.ML_DSA, AlgorithmFamily.SLH_DSA],
        "hybrid_required_until": "2027-01-01",
        "cnsa2_deadline": "2027-01-01",
        "notes": "Long-lived documents must use SLH-DSA-128f minimum for archival integrity.",
    },
    "integrity_hashing": {
        "allowed_families": [AlgorithmFamily.SHA],
        "min_key_size": 256,
        "cnsa2_deadline": "N/A — SHA-256+ already approved",
        "notes": "SHA-256 minimum; SHA-384 preferred for cryptographic commitments.",
    },
}


# ─── Main framework class ──────────────────────────────────────────────────────

class CryptoAgilityFramework:
    """
    Central registry and advisory engine for crypto-agile PQC migration.

    Usage:
        caf = CryptoAgilityFramework()
        caf.recommend_replacement("RSA-2048")
        plan = caf.generate_migration_plan("RSA-2048", "ML-DSA-44", system_count=42)
    """

    def __init__(self) -> None:
        self._registry: Dict[str, CryptoAlgorithm] = {}
        for algo in _BUILTIN_ALGORITHMS:
            self._registry[algo.name] = algo

    # ── Registry management ────────────────────────────────────────────────────

    def register_algorithm(self, algo: CryptoAlgorithm) -> None:
        """Register a custom algorithm (e.g. a vendor extension or draft standard)."""
        self._registry[algo.name] = algo

    def get_algorithm(self, name: str) -> CryptoAlgorithm:
        """Return algorithm by exact name. Raises KeyError if not found."""
        if name not in self._registry:
            raise KeyError(
                f"Algorithm '{name}' not in registry. "
                f"Available: {', '.join(sorted(self._registry))}"
            )
        return self._registry[name]

    def list_all(self) -> List[CryptoAlgorithm]:
        """Return all registered algorithms."""
        return list(self._registry.values())

    # ── Migration advisory ─────────────────────────────────────────────────────

    def list_quantum_vulnerable(self) -> List[CryptoAlgorithm]:
        """Return quantum-vulnerable algorithms sorted by migration_priority (1 = most urgent)."""
        return sorted(
            [a for a in self._registry.values() if a.quantum_vulnerable],
            key=lambda a: a.migration_priority,
        )

    def recommend_replacement(self, current_algo_name: str) -> List[CryptoAlgorithm]:
        """
        Return CNSA 2.0 approved replacement algorithms for the given algorithm.
        Matching is by use-case alignment (family and key size), not just any PQ algo.
        """
        try:
            current = self.get_algorithm(current_algo_name)
        except KeyError:
            return []

        candidates: List[CryptoAlgorithm] = []
        for algo in self._registry.values():
            if not algo.cnsa2_approved:
                continue
            if algo.quantum_vulnerable:
                continue
            if algo.name == current_algo_name:
                continue
            # Family-based matching logic
            if current.family in (AlgorithmFamily.RSA, AlgorithmFamily.ECC, AlgorithmFamily.DH):
                # For asymmetric key exchange → ML-KEM; for signatures → ML-DSA, SLH-DSA
                if current.use_cases and any(
                    kw in " ".join(current.use_cases).lower()
                    for kw in ("signing", "auth", "certificate", "code")
                ):
                    if algo.family in (AlgorithmFamily.ML_DSA, AlgorithmFamily.SLH_DSA):
                        candidates.append(algo)
                else:
                    if algo.family == AlgorithmFamily.ML_KEM:
                        candidates.append(algo)
            elif current.family == AlgorithmFamily.AES:
                if algo.family == AlgorithmFamily.AES and algo.key_size_bits >= 256:
                    candidates.append(algo)
            elif current.family == AlgorithmFamily.SHA:
                if algo.family == AlgorithmFamily.SHA and algo.key_size_bits >= 256:
                    candidates.append(algo)

        # Sort: highest PQ security bits first, then performance
        candidates.sort(key=lambda a: (-a.pq_security_bits, -a.performance_score))
        return candidates

    def generate_migration_plan(
        self,
        from_algo: str,
        to_algo: str,
        system_count: int,
    ) -> MigrationPlan:
        """
        Generate a phased migration plan from one algorithm to another.
        Risk and effort scale with system count and algorithm families.
        """
        try:
            src = self.get_algorithm(from_algo)
            dst = self.get_algorithm(to_algo)
        except KeyError as exc:
            raise ValueError(str(exc)) from exc

        # Base effort estimates per system (person-days)
        effort_per_system = 3.0
        if src.family in (AlgorithmFamily.RSA, AlgorithmFamily.ECC):
            effort_per_system += 2.0   # PKI changes need CA coordination
        if dst.family in (AlgorithmFamily.ML_DSA, AlgorithmFamily.SLH_DSA):
            effort_per_system += 1.5   # Larger signatures → app changes
        if dst.family == AlgorithmFamily.ML_KEM:
            effort_per_system += 1.0   # KEM API differs from DH/ECDH

        total_effort = round(effort_per_system * system_count)
        # Duration: assume 2 person-days per calendar day for migration work
        estimated_days = max(30, min(540, round(total_effort / 2)))

        # Risk level
        if system_count > 100 or src.migration_priority == 1:
            risk_level = "HIGH"
        elif system_count > 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        phases = [
            {
                "phase": 1,
                "name": "Discovery & CBOM",
                "duration_days": max(7, estimated_days // 6),
                "activities": [
                    f"Inventory all {system_count} systems using {from_algo}",
                    "Classify data sensitivity and HNDL exposure per system",
                    "Generate CBOM entries for each affected asset",
                    "Identify dependencies: libraries, HSMs, certificates, protocols",
                ],
                "exit_criteria": "100% CBOM coverage; HNDL risk scored per system",
            },
            {
                "phase": 2,
                "name": "Lab Validation",
                "duration_days": max(14, estimated_days // 5),
                "activities": [
                    f"Deploy {to_algo} in isolated lab environment",
                    "Benchmark performance: latency, throughput, key-gen time",
                    "Run interoperability tests with all peer systems",
                    "Verify hybrid mode operation if applicable",
                    "Security review of new algorithm integration code",
                ],
                "exit_criteria": f"All {to_algo} tests pass; performance within 20% of baseline",
            },
            {
                "phase": 3,
                "name": "Hybrid Deployment",
                "duration_days": max(30, estimated_days // 3),
                "activities": [
                    f"Deploy hybrid {from_algo} + {to_algo} on pilot systems (10% of {system_count})",
                    "Monitor for errors, latency regressions, compatibility issues",
                    "Train operations teams on new key management procedures",
                    "Update runbooks, SOPs, and monitoring dashboards",
                    "Phased rollout to remaining systems with per-system validation",
                ],
                "exit_criteria": f"All {system_count} systems running hybrid mode; zero P1 incidents",
            },
            {
                "phase": 4,
                "name": f"Pure {to_algo} Cutover",
                "duration_days": max(14, estimated_days // 4),
                "activities": [
                    f"Disable {from_algo} leg on all systems",
                    "Rotate all affected keys/certificates to pure {to_algo}",
                    "Verify no {from_algo} usage in network captures",
                    "Update firewall/IDS signatures for new algorithm patterns",
                ],
                "exit_criteria": f"Zero {from_algo} traffic; all certs/keys issued as {to_algo}",
            },
            {
                "phase": 5,
                "name": "Validation & Closure",
                "duration_days": max(7, estimated_days // 8),
                "activities": [
                    "Third-party cryptographic audit of migrated systems",
                    "Update CBOM to reflect new algorithm state",
                    "Close migration tickets; archive rollback packages",
                    "Update crypto-agility policy to reflect completed migration",
                    "Publish migration completion report to CISO",
                ],
                "exit_criteria": "Audit passed; CBOM updated; policy updated; CISO sign-off",
            },
        ]

        rollback_path = (
            f"Keep {from_algo} libraries/configurations pinned under feature-flag "
            f"'crypto_legacy_{from_algo.lower().replace('-','_')}'. "
            f"Re-enable via config change (no code deploy) within 4 hours. "
            f"Dual-sign/hybrid mode automatically provides instant rollback at Phase 3."
        )

        testing_requirements = [
            f"Unit tests: verify {to_algo} key-gen, encapsulation, decapsulation/signing/verification",
            "Integration tests: full handshake with each peer system type",
            f"Performance test: {to_algo} under production load (p99 latency ≤ 2× baseline)",
            "Regression suite: all existing cryptographic paths must pass",
            "Interoperability test: cross-vendor validation (OQS-OpenSSL, liboqs, Bouncy Castle)",
            "Fuzzing: malformed key/ciphertext inputs to new algorithm handler",
            "HNDL simulation: verify no legacy algorithm traffic post-cutover",
            "Key rotation test: rotate keys without service disruption",
        ]

        return MigrationPlan(
            from_algo=from_algo,
            to_algo=to_algo,
            system_count=system_count,
            phases=phases,
            estimated_days=estimated_days,
            effort_person_days=total_effort,
            risk_level=risk_level,
            rollback_path=rollback_path,
            testing_requirements=testing_requirements,
        )

    # ── Hybrid compatibility ───────────────────────────────────────────────────

    def check_hybrid_compatibility(
        self, classical_algo: str, pq_algo: str
    ) -> Dict[str, Any]:
        """
        Check whether a classical + PQ algorithm pair is recommended for hybrid mode.
        Returns dict with: compatible(bool), notes(str), recommendation(str).
        """
        key = (classical_algo, pq_algo)
        if key in _HYBRID_COMPATIBILITY:
            compatible, notes = _HYBRID_COMPATIBILITY[key]
            recommendation = (
                f"Use {classical_algo}+{pq_algo} hybrid mode. {notes}"
                if compatible
                else f"Do NOT use this pair. {notes}"
            )
        else:
            # Heuristic fallback
            try:
                c = self.get_algorithm(classical_algo)
                p = self.get_algorithm(pq_algo)
                compatible = (not p.quantum_vulnerable) and (p.cnsa2_approved)
                notes = (
                    "Pair not in explicit compatibility table; "
                    "heuristic based on algorithm properties. Validate with OQS test suite."
                )
                recommendation = (
                    f"Likely compatible but not validated in registry. {notes}"
                    if compatible
                    else f"Incompatible: {pq_algo} is not CNSA 2.0 approved or quantum-vulnerable."
                )
            except KeyError:
                compatible = False
                notes = "One or both algorithms not found in registry."
                recommendation = "Cannot assess compatibility — unknown algorithm(s)."

        return {
            "classical_algo": classical_algo,
            "pq_algo": pq_algo,
            "compatible": compatible,
            "notes": notes,
            "recommendation": recommendation,
            "references": [
                "RFC 9370 — Multiple Key Exchanges in IKEv2",
                "IETF draft-ietf-tls-hybrid-design — Hybrid Key Exchange in TLS 1.3",
                "NIST SP 800-227 — Recommendations for Key-Establishment Methods",
            ],
        }

    # ── Policy-as-code ─────────────────────────────────────────────────────────

    def policy_as_code_check(self, algorithm_name: str, use_case: str) -> Dict[str, Any]:
        """
        Check whether an algorithm is policy-allowed for a given use case.

        Args:
            algorithm_name: e.g. "RSA-2048"
            use_case: e.g. "tls13_key_exchange", "code_signing"

        Returns dict with: allowed(bool), reason(str), cnsa2_deadline, recommendation.
        """
        policy = _USE_CASE_POLICY.get(use_case)
        if policy is None:
            return {
                "algorithm": algorithm_name,
                "use_case": use_case,
                "allowed": None,
                "reason": f"Use case '{use_case}' not in policy registry.",
                "cnsa2_deadline": "N/A",
                "recommendation": (
                    f"Define a policy for '{use_case}' or use one of: "
                    + ", ".join(_USE_CASE_POLICY.keys())
                ),
            }

        try:
            algo = self.get_algorithm(algorithm_name)
        except KeyError:
            return {
                "algorithm": algorithm_name,
                "use_case": use_case,
                "allowed": False,
                "reason": f"Algorithm '{algorithm_name}' not found in registry.",
                "cnsa2_deadline": "N/A",
                "recommendation": "Register the algorithm before running a policy check.",
            }

        allowed_families = policy.get("allowed_families", [])
        min_key_size = policy.get("min_key_size", 0)

        family_ok = algo.family in allowed_families
        size_ok = algo.key_size_bits >= min_key_size

        allowed = family_ok and size_ok and not algo.quantum_vulnerable

        if not family_ok:
            reason = (
                f"{algorithm_name} (family: {algo.family.value}) is not in the allowed "
                f"families for '{use_case}': "
                + ", ".join(f.value for f in allowed_families)
                + "."
            )
        elif not size_ok:
            reason = (
                f"{algorithm_name} key size ({algo.key_size_bits} bits) is below the "
                f"policy minimum of {min_key_size} bits for '{use_case}'."
            )
        elif algo.quantum_vulnerable:
            reason = (
                f"{algorithm_name} is quantum-vulnerable and must not be used for "
                f"'{use_case}' after {algo.cnsa2_deadline}."
            )
        else:
            reason = (
                f"{algorithm_name} is CNSA 2.0 approved and within policy for '{use_case}'."
            )

        replacements = self.recommend_replacement(algorithm_name)
        rec_names = [r.name for r in replacements[:3]]

        return {
            "algorithm": algorithm_name,
            "use_case": use_case,
            "allowed": allowed,
            "reason": reason,
            "cnsa2_deadline": algo.cnsa2_deadline,
            "recommendation": (
                f"Replace with one of: {', '.join(rec_names)}"
                if rec_names and not allowed
                else policy.get("notes", "No additional recommendation.")
            ),
        }

    # ── Inventory scan ─────────────────────────────────────────────────────────

    def crypto_inventory_scan(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan a configuration dictionary for algorithm names and assess vulnerability.

        config_dict keys are component names; values are strings or lists of strings
        containing algorithm names (e.g. "RSA-2048", "AES-128").

        Returns found algorithms, per-component analysis, vulnerable count, urgency.
        """
        found_algos: Dict[str, List[str]] = {}    # component → list of algo names
        vulnerable_components: List[Dict[str, Any]] = []
        safe_components: List[Dict[str, Any]] = []
        unknown_algorithms: List[str] = []

        for component, value in config_dict.items():
            algo_names: List[str] = []
            if isinstance(value, str):
                algo_names = [value]
            elif isinstance(value, list):
                algo_names = [str(v) for v in value]

            found_algos[component] = algo_names
            for algo_name in algo_names:
                if algo_name in self._registry:
                    algo = self._registry[algo_name]
                    entry = {
                        "component": component,
                        "algorithm": algo_name,
                        "family": algo.family.value,
                        "status": algo.status.value,
                        "migration_priority": algo.migration_priority,
                        "cnsa2_deadline": algo.cnsa2_deadline,
                    }
                    if algo.quantum_vulnerable:
                        entry["action"] = "REPLACE — quantum-vulnerable"
                        vulnerable_components.append(entry)
                    else:
                        entry["action"] = "KEEP — quantum-safe"
                        safe_components.append(entry)
                else:
                    unknown_algorithms.append(algo_name)

        vulnerable_count = len(vulnerable_components)
        if vulnerable_count == 0:
            urgency = "NONE"
            urgency_reason = "No quantum-vulnerable algorithms detected."
        elif vulnerable_count <= 2:
            urgency = "LOW"
            urgency_reason = f"{vulnerable_count} component(s) need migration; plan within 12 months."
        elif vulnerable_count <= 5:
            urgency = "MEDIUM"
            urgency_reason = f"{vulnerable_count} vulnerable components; begin migration within 6 months."
        else:
            urgency = "HIGH"
            urgency_reason = f"{vulnerable_count} vulnerable components; immediate migration planning required."

        return {
            "scan_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "components_scanned": len(config_dict),
            "algorithms_found": sum(len(v) for v in found_algos.values()),
            "vulnerable_count": vulnerable_count,
            "safe_count": len(safe_components),
            "unknown_count": len(unknown_algorithms),
            "migration_urgency": urgency,
            "urgency_reason": urgency_reason,
            "vulnerable_components": vulnerable_components,
            "safe_components": safe_components,
            "unknown_algorithms": unknown_algorithms,
        }

    # ── Agility score ──────────────────────────────────────────────────────────

    def agility_score(
        self,
        system_name: str,
        algorithms_in_use: List[str],
        abstraction_layers: int = 0,
        hardcoded_count: int = 0,
        crypto_test_coverage_pct: float = 0.0,
        config_driven: bool = False,
        key_rotation_automated: bool = False,
    ) -> Dict[str, Any]:
        """
        Score how crypto-agile a system is (0–100).

        Dimensions:
          - Algorithm diversity (0-20): not relying on a single family
          - PQ readiness (0-25): fraction of algorithms that are quantum-safe
          - Abstraction (0-20): abstraction layers isolate algo from business logic
          - Configurability (0-15): algorithms driven by config, not hardcoded
          - Test coverage (0-10): crypto-path unit test coverage
          - Key rotation (0-10): automated key rotation in place

        Returns dict with: score(float), breakdown(dict), grade(str), gaps(list).
        """
        used_algos = [
            self._registry[n] for n in algorithms_in_use if n in self._registry
        ]
        total = len(used_algos)

        # 1. Algorithm diversity
        families = {a.family for a in used_algos}
        diversity_score = min(20.0, len(families) * 4.0)

        # 2. PQ readiness
        pq_safe = sum(1 for a in used_algos if not a.quantum_vulnerable)
        pq_score = (pq_safe / total * 25.0) if total > 0 else 0.0

        # 3. Abstraction layers
        abstraction_score = min(20.0, abstraction_layers * 5.0)

        # 4. Configurability
        if config_driven:
            config_score = 15.0 - min(15.0, hardcoded_count * 3.0)
        else:
            config_score = max(0.0, 5.0 - hardcoded_count * 1.5)

        # 5. Test coverage
        test_score = min(10.0, crypto_test_coverage_pct / 10.0)

        # 6. Key rotation
        rotation_score = 10.0 if key_rotation_automated else 0.0

        total_score = round(
            diversity_score + pq_score + abstraction_score
            + config_score + test_score + rotation_score,
            1,
        )

        if total_score >= 80:
            grade = "A — Highly Agile"
        elif total_score >= 65:
            grade = "B — Moderately Agile"
        elif total_score >= 45:
            grade = "C — Partially Agile"
        elif total_score >= 25:
            grade = "D — Low Agility"
        else:
            grade = "F — Crypto-Rigid (High Risk)"

        gaps = []
        if pq_score < 20:
            vulnerable = [a.name for a in used_algos if a.quantum_vulnerable]
            gaps.append(f"PQ gap: {len(vulnerable)} quantum-vulnerable algorithm(s): {', '.join(vulnerable)}")
        if abstraction_score < 10:
            gaps.append("Low abstraction: algorithms likely hardcoded in business logic; add crypto provider layer")
        if not config_driven:
            gaps.append("Configurability gap: algorithm selection not driven by configuration")
        if hardcoded_count > 2:
            gaps.append(f"Hardcoded algorithms: {hardcoded_count} instances detected; externalize to config")
        if crypto_test_coverage_pct < 50:
            gaps.append(f"Test coverage: {crypto_test_coverage_pct:.0f}% crypto-path coverage; target ≥80%")
        if not key_rotation_automated:
            gaps.append("Key rotation: not automated; manual rotation increases HNDL window")

        return {
            "system": system_name,
            "score": total_score,
            "grade": grade,
            "breakdown": {
                "algorithm_diversity": round(diversity_score, 1),
                "pq_readiness": round(pq_score, 1),
                "abstraction_layers": round(abstraction_score, 1),
                "configurability": round(config_score, 1),
                "test_coverage": round(test_score, 1),
                "key_rotation": round(rotation_score, 1),
            },
            "gaps": gaps,
            "algorithms_assessed": [a.name for a in used_algos],
            "assessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # ── CBOM generation ────────────────────────────────────────────────────────

    def generate_cbom(
        self,
        system_name: str,
        algorithms: List[str],
        version: str = "1.4",
        manufacturer: str = "Internal",
    ) -> Dict[str, Any]:
        """
        Generate a Crypto Bill of Materials in CycloneDX 1.4 cryptographicAsset format.

        See: https://cyclonedx.org/capabilities/cbom/
        """
        components = []
        for algo_name in algorithms:
            if algo_name not in self._registry:
                components.append({
                    "type": "cryptographic-asset",
                    "bom-ref": f"crypto-{hashlib.md5(algo_name.encode()).hexdigest()[:8]}",
                    "name": algo_name,
                    "cryptoProperties": {
                        "assetType": "algorithm",
                        "algorithmProperties": {
                            "primitive": "unknown",
                            "parameterSetIdentifier": "unknown",
                        },
                    },
                    "evidence": {"occurrence": [{"location": system_name}]},
                    "tags": ["unknown", "needs-review"],
                })
                continue

            algo = self._registry[algo_name]
            prim = {
                AlgorithmFamily.RSA: "public-key-encryption",
                AlgorithmFamily.ECC: "signature",
                AlgorithmFamily.DH:  "key-agreement",
                AlgorithmFamily.AES: "block-cipher",
                AlgorithmFamily.SHA: "hash",
                AlgorithmFamily.ML_KEM: "kem",
                AlgorithmFamily.ML_DSA: "signature",
                AlgorithmFamily.SLH_DSA: "signature",
                AlgorithmFamily.BIKE: "kem",
                AlgorithmFamily.MCELIECE: "kem",
                AlgorithmFamily.QRNG: "other",
            }.get(algo.family, "other")

            tags = ["quantum-safe"] if not algo.quantum_vulnerable else ["quantum-vulnerable", "needs-migration"]
            if algo.cnsa2_approved:
                tags.append("cnsa2-approved")

            components.append({
                "type": "cryptographic-asset",
                "bom-ref": f"crypto-{hashlib.md5(algo_name.encode()).hexdigest()[:8]}",
                "name": algo_name,
                "version": "1.0",
                "manufacturer": manufacturer,
                "cryptoProperties": {
                    "assetType": "algorithm",
                    "algorithmProperties": {
                        "primitive": prim,
                        "parameterSetIdentifier": str(algo.key_size_bits),
                        "executionEnvironment": "software",
                        "implementationPlatform": "x86_64",
                        "certificationLevel": "fips-140-2" if algo.cnsa2_approved else "none",
                        "quantumSafe": not algo.quantum_vulnerable,
                        "nistStandard": algo.nist_standard,
                    },
                },
                "properties": [
                    {"name": "crypto:migrationPriority",   "value": str(algo.migration_priority)},
                    {"name": "crypto:cnsa2Deadline",        "value": algo.cnsa2_deadline},
                    {"name": "crypto:performanceScore",     "value": str(algo.performance_score)},
                    {"name": "crypto:pqSecurityBits",       "value": str(algo.pq_security_bits)},
                ],
                "evidence": {"occurrence": [{"location": system_name}]},
                "tags": tags,
            })

        vulnerable_count = sum(
            1 for a in algorithms
            if a in self._registry and self._registry[a].quantum_vulnerable
        )

        return {
            "bomFormat": "CycloneDX",
            "specVersion": version,
            "serialNumber": f"urn:uuid:{hashlib.md5(system_name.encode()).hexdigest()}",
            "version": 1,
            "metadata": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tools": [{"vendor": "QuantumSecurityLab", "name": "CryptoAgilityFramework", "version": "1.0"}],
                "component": {
                    "type": "application",
                    "name": system_name,
                    "manufacturer": manufacturer,
                },
            },
            "components": components,
            "summary": {
                "total_algorithms": len(algorithms),
                "quantum_vulnerable": vulnerable_count,
                "quantum_safe": len(algorithms) - vulnerable_count,
                "cnsa2_approved": sum(
                    1 for a in algorithms
                    if a in self._registry and self._registry[a].cnsa2_approved
                ),
            },
        }


# ─── Module-level convenience instance ────────────────────────────────────────

_default_framework = CryptoAgilityFramework()


def get_framework() -> CryptoAgilityFramework:
    """Return the shared module-level framework instance."""
    return _default_framework


# ─── Quick smoke-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    caf = CryptoAgilityFramework()

    print("=== Quantum-Vulnerable Algorithms (top 5) ===")
    for a in caf.list_quantum_vulnerable()[:5]:
        print(f"  [{a.migration_priority}] {a.name} — {a.family.value} — deadline {a.cnsa2_deadline}")

    print("\n=== Replacements for RSA-2048 ===")
    for r in caf.recommend_replacement("RSA-2048"):
        print(f"  {r.name} ({r.nist_standard}) — PQ bits: {r.pq_security_bits}")

    print("\n=== Migration Plan: RSA-2048 → ML-DSA-65, 50 systems ===")
    plan = caf.generate_migration_plan("RSA-2048", "ML-DSA-65", 50)
    print(f"  Effort: {plan.effort_person_days} person-days over {plan.estimated_days} days ({plan.risk_level} risk)")

    print("\n=== Hybrid Compatibility: X25519 + ML-KEM-768 ===")
    compat = caf.check_hybrid_compatibility("X25519", "ML-KEM-768")
    print(f"  Compatible: {compat['compatible']} — {compat['notes']}")

    print("\n=== Policy Check: RSA-2048 for tls13_key_exchange ===")
    policy = caf.policy_as_code_check("RSA-2048", "tls13_key_exchange")
    print(f"  Allowed: {policy['allowed']} — {policy['reason']}")

    print("\n=== Agility Score: example-webapp ===")
    score = caf.agility_score(
        "example-webapp",
        ["RSA-2048", "AES-256", "SHA-256"],
        abstraction_layers=1,
        hardcoded_count=2,
        crypto_test_coverage_pct=40.0,
        config_driven=False,
        key_rotation_automated=False,
    )
    print(f"  Score: {score['score']}/100 — {score['grade']}")

    print("\n=== CBOM: example-webapp ===")
    cbom = caf.generate_cbom("example-webapp", ["RSA-2048", "AES-256", "ML-KEM-768"])
    print(f"  Components: {len(cbom['components'])}  Vulnerable: {cbom['summary']['quantum_vulnerable']}")
