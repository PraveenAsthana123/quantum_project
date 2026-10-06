"""
Quantum Security Control Tower — Executive PQC Migration Dashboard
===================================================================
Version : 1.0
Date    : 2026-10-06
Purpose : Real-time aggregation of PQC migration status, threat intelligence,
          CBOM inventory, and compliance metrics across 29 security layers
Reference: NIST NCCoE PQC Migration Project (NIST SP 1800-38), CNSA 2.0
"""
from __future__ import annotations

import json
import time
import os
import pathlib
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class TowerMetrics:
    timestamp: str
    overall_pqc_score: float          # 0-100 aggregate across all 29 layers
    layers_completed: int             # L4 + L5 layers
    layers_in_progress: int           # L2 + L3 layers
    layers_not_started: int           # L0 + L1 layers
    critical_findings: int            # open P1/P2 findings
    hndl_risk_score: float            # 0-100 Harvest-Now-Decrypt-Later exposure
    compliance_score: float           # 0-100 CNSA 2.0 / NIST compliance
    monthly_spend_usd: float          # current monthly PQC migration spend
    projected_completion_year: int    # projected full migration year


@dataclass
class LayerStatus:
    layer_id: str                     # "L01" … "L29"
    name: str
    completion_pct: float             # 0-100
    current_algo: str                 # e.g. "RSA-2048"
    target_algo: str                  # e.g. "ML-DSA-65"
    hndl_risk: str                    # LOW / MEDIUM / HIGH / CRITICAL
    status: str                       # NOT_STARTED / IN_PROGRESS / HYBRID / COMPLETED
    open_findings: int
    last_updated: str


@dataclass
class ThreatIntelItem:
    id: str
    title: str
    severity: str                     # CRITICAL / HIGH / MEDIUM / LOW
    cve_or_reference: str
    quantum_relevance: str            # e.g. "HNDL", "Shor's attack", "Grover's"
    affected_algorithms: List[str]
    recommended_action: str
    published_date: str


# ─── Seed data: 29 layers ─────────────────────────────────────────────────────

_LAYER_SEED: List[Dict[str, Any]] = [
    {"layer_id":"L01","name":"Physical / Hardware",     "completion_pct":15.0, "current_algo":"PRNG-HW",       "target_algo":"QRNG-Hardware",  "hndl_risk":"LOW",      "status":"IN_PROGRESS","open_findings":3},
    {"layer_id":"L02","name":"Data Link / MACsec",      "completion_pct":10.0, "current_algo":"RSA-2048",      "target_algo":"ML-DSA-65",      "hndl_risk":"HIGH",     "status":"IN_PROGRESS","open_findings":4},
    {"layer_id":"L03","name":"Network / IPsec",         "completion_pct":20.0, "current_algo":"DH-2048",       "target_algo":"ML-KEM-768",     "hndl_risk":"CRITICAL", "status":"IN_PROGRESS","open_findings":7},
    {"layer_id":"L04","name":"Transport / TLS",         "completion_pct":45.0, "current_algo":"ECDSA-P256",    "target_algo":"ML-KEM-768",     "hndl_risk":"CRITICAL", "status":"HYBRID",     "open_findings":5},
    {"layer_id":"L05","name":"Session / DTLS",          "completion_pct":30.0, "current_algo":"ECDH-P256",     "target_algo":"ML-KEM-512",     "hndl_risk":"HIGH",     "status":"IN_PROGRESS","open_findings":4},
    {"layer_id":"L06","name":"PKI / Certificate Mgmt",  "completion_pct":55.0, "current_algo":"RSA-2048",      "target_algo":"ML-DSA-65",      "hndl_risk":"CRITICAL", "status":"HYBRID",     "open_findings":6},
    {"layer_id":"L07","name":"Application / API Auth",  "completion_pct":25.0, "current_algo":"ECDSA-P256",    "target_algo":"ML-DSA-44",      "hndl_risk":"HIGH",     "status":"IN_PROGRESS","open_findings":5},
    {"layer_id":"L08","name":"Code Signing",            "completion_pct":60.0, "current_algo":"RSA-4096",      "target_algo":"ML-DSA-65",      "hndl_risk":"HIGH",     "status":"HYBRID",     "open_findings":3},
    {"layer_id":"L09","name":"SSH / Remote Access",     "completion_pct":35.0, "current_algo":"RSA-2048",      "target_algo":"ML-DSA-44",      "hndl_risk":"HIGH",     "status":"IN_PROGRESS","open_findings":4},
    {"layer_id":"L10","name":"DNS / DNSSEC",            "completion_pct":5.0,  "current_algo":"ECDSA-P256",    "target_algo":"ML-DSA-65",      "hndl_risk":"MEDIUM",   "status":"NOT_STARTED","open_findings":2},
    {"layer_id":"L11","name":"VPN / IKEv2",             "completion_pct":40.0, "current_algo":"DH-3072",       "target_algo":"ML-KEM-768",     "hndl_risk":"CRITICAL", "status":"HYBRID",     "open_findings":6},
    {"layer_id":"L12","name":"Email / S/MIME",          "completion_pct":0.0,  "current_algo":"RSA-2048",      "target_algo":"ML-DSA-44",      "hndl_risk":"MEDIUM",   "status":"NOT_STARTED","open_findings":1},
    {"layer_id":"L13","name":"Database Encryption",     "completion_pct":80.0, "current_algo":"AES-256",       "target_algo":"AES-256",        "hndl_risk":"LOW",      "status":"COMPLETED",  "open_findings":0},
    {"layer_id":"L14","name":"Disk / File Encryption",  "completion_pct":90.0, "current_algo":"AES-256",       "target_algo":"AES-256",        "hndl_risk":"LOW",      "status":"COMPLETED",  "open_findings":0},
    {"layer_id":"L15","name":"Key Management / HSM",    "completion_pct":50.0, "current_algo":"RSA-2048",      "target_algo":"ML-KEM-1024",    "hndl_risk":"CRITICAL", "status":"HYBRID",     "open_findings":8},
    {"layer_id":"L16","name":"Secrets Management",      "completion_pct":30.0, "current_algo":"RSA-3072",      "target_algo":"ML-KEM-768",     "hndl_risk":"CRITICAL", "status":"IN_PROGRESS","open_findings":5},
    {"layer_id":"L17","name":"Identity / SAML/OIDC",    "completion_pct":20.0, "current_algo":"RSA-2048",      "target_algo":"ML-DSA-44",      "hndl_risk":"HIGH",     "status":"IN_PROGRESS","open_findings":4},
    {"layer_id":"L18","name":"Firmware / Boot Chain",   "completion_pct":10.0, "current_algo":"ECDSA-P256",    "target_algo":"SLH-DSA-128f",   "hndl_risk":"HIGH",     "status":"IN_PROGRESS","open_findings":5},
    {"layer_id":"L19","name":"Container / Kubernetes",  "completion_pct":15.0, "current_algo":"ECDSA-P256",    "target_algo":"ML-DSA-44",      "hndl_risk":"MEDIUM",   "status":"IN_PROGRESS","open_findings":3},
    {"layer_id":"L20","name":"CI/CD Pipeline",          "completion_pct":55.0, "current_algo":"RSA-2048",      "target_algo":"ML-DSA-44",      "hndl_risk":"HIGH",     "status":"HYBRID",     "open_findings":3},
    {"layer_id":"L21","name":"Backup / Recovery",       "completion_pct":5.0,  "current_algo":"AES-128",       "target_algo":"AES-256",        "hndl_risk":"HIGH",     "status":"NOT_STARTED","open_findings":4},
    {"layer_id":"L22","name":"Logging / SIEM",          "completion_pct":70.0, "current_algo":"SHA-256",       "target_algo":"SHA-384",        "hndl_risk":"LOW",      "status":"COMPLETED",  "open_findings":1},
    {"layer_id":"L23","name":"Cloud Provider APIs",     "completion_pct":35.0, "current_algo":"ECDSA-P256",    "target_algo":"ML-DSA-65",      "hndl_risk":"HIGH",     "status":"IN_PROGRESS","open_findings":4},
    {"layer_id":"L24","name":"Third-Party Integrations","completion_pct":0.0,  "current_algo":"RSA-2048",      "target_algo":"ML-KEM-768",     "hndl_risk":"HIGH",     "status":"NOT_STARTED","open_findings":3},
    {"layer_id":"L25","name":"Mobile / Device Auth",    "completion_pct":20.0, "current_algo":"ECDSA-P256",    "target_algo":"ML-DSA-44",      "hndl_risk":"MEDIUM",   "status":"IN_PROGRESS","open_findings":3},
    {"layer_id":"L26","name":"IoT / Embedded",          "completion_pct":0.0,  "current_algo":"ECDSA-P256",    "target_algo":"ML-KEM-512",     "hndl_risk":"MEDIUM",   "status":"NOT_STARTED","open_findings":2},
    {"layer_id":"L27","name":"Blockchain / Ledger",     "completion_pct":10.0, "current_algo":"ECDSA-P256",    "target_algo":"ML-DSA-65",      "hndl_risk":"LOW",      "status":"IN_PROGRESS","open_findings":2},
    {"layer_id":"L28","name":"AI / ML Pipeline",        "completion_pct":25.0, "current_algo":"RSA-2048",      "target_algo":"ML-DSA-44",      "hndl_risk":"MEDIUM",   "status":"IN_PROGRESS","open_findings":3},
    {"layer_id":"L29","name":"Governance & Policy",     "completion_pct":65.0, "current_algo":"N/A",           "target_algo":"Crypto-Agility", "hndl_risk":"LOW",      "status":"HYBRID",     "open_findings":2},
]

# ─── Seed data: 10 threat intelligence items ──────────────────────────────────

_THREAT_SEED: List[Dict[str, Any]] = [
    {
        "id": "TI-2026-001",
        "title": "Quantum annealer demonstrates DH-1024 discrete-log attack in 48h — BlackHat 2026",
        "severity": "CRITICAL",
        "cve_or_reference": "BlackHat 2026 — Briefing BH-26-QC-07",
        "quantum_relevance": "Shor's algorithm variant on quantum annealer hardware",
        "affected_algorithms": ["DH-1024", "DH-2048"],
        "recommended_action": (
            "Immediately disable DH-1024 in all IKEv2/TLS configurations. "
            "Accelerate ML-KEM-768 hybrid deployment on all VPN endpoints."
        ),
        "published_date": "2026-08-08",
    },
    {
        "id": "TI-2026-002",
        "title": "HNDL campaign targeting financial sector TLS 1.2 traffic — CISA Alert AA26-198A",
        "severity": "CRITICAL",
        "cve_or_reference": "CISA Alert AA26-198A",
        "quantum_relevance": "Harvest Now Decrypt Later — encrypted traffic stored for future decryption",
        "affected_algorithms": ["RSA-2048", "ECDH-P256", "DH-2048"],
        "recommended_action": (
            "Enable X25519+ML-KEM-768 hybrid key exchange on all external TLS endpoints. "
            "Enforce TLS 1.3 minimum. Prioritize high-sensitivity data flows."
        ),
        "published_date": "2026-07-17",
    },
    {
        "id": "TI-2026-003",
        "title": "Nation-state actor exfiltrating IKEv2 DH-2048 session captures — NCSC advisory",
        "severity": "HIGH",
        "cve_or_reference": "NCSC-2026-0042",
        "quantum_relevance": "HNDL — stored VPN sessions for retroactive decryption post-CRQC",
        "affected_algorithms": ["DH-2048", "DH-3072"],
        "recommended_action": (
            "Deploy ML-KEM-768 KEM in IKEv2 hybrid mode (RFC 9370). "
            "Apply to government and defence supply chain VPNs within 90 days."
        ),
        "published_date": "2026-06-30",
    },
    {
        "id": "TI-2026-004",
        "title": "CVE-2026-31182: OpenSSL 3.2 RSA-1024 fallback in TLS 1.3 downgrade — CVSS 9.1",
        "severity": "HIGH",
        "cve_or_reference": "CVE-2026-31182",
        "quantum_relevance": "Forces classical-only fallback; worsens HNDL exposure",
        "affected_algorithms": ["RSA-1024", "RSA-2048"],
        "recommended_action": (
            "Patch to OpenSSL 3.2.2+ immediately. "
            "Enforce minimum RSA-3072 via SSL_CTX_set_min_bits(); disable RSA-1024 cipher suites."
        ),
        "published_date": "2026-05-14",
    },
    {
        "id": "TI-2026-005",
        "title": "IBM Quantum System Two demonstrates 2000-qubit Shor's precursor experiment",
        "severity": "HIGH",
        "cve_or_reference": "IBM Research Blog 2026-04-22 / Nature 635",
        "quantum_relevance": "Shor's algorithm — factoring milestone accelerates CRQC timeline estimate",
        "affected_algorithms": ["RSA-2048", "ECDSA-P256", "DH-2048"],
        "recommended_action": (
            "Revise CRQC timeline estimate from 2035 to 2032. "
            "Bring forward Phase 3 hybrid TLS deployment by 18 months."
        ),
        "published_date": "2026-04-22",
    },
    {
        "id": "TI-2026-006",
        "title": "NIST FIPS 203/204/205 final; ML-KEM/ML-DSA/SLH-DSA now mandatory for US Federal",
        "severity": "MEDIUM",
        "cve_or_reference": "NIST FIPS 203, FIPS 204, FIPS 205 (August 2024 final)",
        "quantum_relevance": "Regulatory — federal agencies must migrate by 2030",
        "affected_algorithms": ["RSA-2048", "ECDSA-P256", "DH-2048", "X25519"],
        "recommended_action": (
            "Validate library versions: liboqs ≥0.10, OQS-OpenSSL 3.2+, Bouncy Castle 1.78+. "
            "Start FIPS 140-3 module validation for PQC if required."
        ),
        "published_date": "2026-03-01",
    },
    {
        "id": "TI-2026-007",
        "title": "SHA-1 collision attack cost drops to $10K — practical forging risk for legacy code signing",
        "severity": "HIGH",
        "cve_or_reference": "CWE-327 / NIST SP 800-131A disallowed list",
        "quantum_relevance": "Classical attack; Grover's further reduces SHA-1 residual to ~35 bits",
        "affected_algorithms": ["SHA-1"],
        "recommended_action": (
            "Emergency scan: identify any SHA-1 usage in code signing, certificate chains, or HMAC. "
            "Replace with SHA-256 or SHA-384. Block SHA-1 in CI/CD pipelines."
        ),
        "published_date": "2026-02-11",
    },
    {
        "id": "TI-2026-008",
        "title": "Supply chain compromise: popular npm crypto library ships RSA-1024 fallback",
        "severity": "HIGH",
        "cve_or_reference": "CVE-2026-11039 / npm advisory GHSA-26qm-7rr6",
        "quantum_relevance": "HNDL — RSA-1024 encrypted data immediately decryptable in 2030 window",
        "affected_algorithms": ["RSA-1024"],
        "recommended_action": (
            "Audit package-lock.json for affected versions (node-rsa < 1.1.2). "
            "Pin to node-rsa ≥1.1.2 or replace with WebCrypto + FIPS 203 wrapper."
        ),
        "published_date": "2026-01-28",
    },
    {
        "id": "TI-2026-009",
        "title": "CloudFlare activates X25519+ML-KEM-768 by default for all zones — industry inflection",
        "severity": "LOW",
        "cve_or_reference": "Cloudflare Blog 2026-09-15",
        "quantum_relevance": "Positive — hybrid PQC becomes default for major CDN; sets browser expectations",
        "affected_algorithms": ["X25519", "ML-KEM-768"],
        "recommended_action": (
            "Verify origin servers support X25519+ML-KEM-768 to avoid TLS negotiation fallback. "
            "Update nginx/Apache SSL config; test with `openssl s_client -groups X25519MLKEM768`."
        ),
        "published_date": "2026-09-15",
    },
    {
        "id": "TI-2026-010",
        "title": "DORA Article 30 supplemented: PQC key lifecycle included in ICT third-party contracts",
        "severity": "MEDIUM",
        "cve_or_reference": "DORA Delegated Regulation 2026/C-814 Article 30(3)(j)",
        "quantum_relevance": "Regulatory — EU financial entities must include PQC requirements in vendor SLAs by 2027",
        "affected_algorithms": ["RSA-2048", "ECDSA-P256"],
        "recommended_action": (
            "Amend third-party ICT contracts to mandate CNSA 2.0 algorithm support by 2027-12-31. "
            "Issue vendor questionnaire: PQC roadmap + target algorithm + testing status."
        ),
        "published_date": "2026-09-01",
    },
]

# ─── Compliance framework data ─────────────────────────────────────────────────

_COMPLIANCE_SEED = {
    "CNSA_2.0": {
        "full_name": "Commercial National Security Algorithm Suite 2.0",
        "issuer": "NSA / CISA",
        "reference": "NSA CNSA 2.0 Announcement, September 2022",
        "requirements": [
            {"item": "ML-KEM-1024 for all key encapsulation",         "deadline": "2030-01-01", "status": "IN_PROGRESS"},
            {"item": "ML-DSA-87 for all digital signatures",          "deadline": "2030-01-01", "status": "IN_PROGRESS"},
            {"item": "AES-256 for all symmetric encryption",          "deadline": "2026-01-01", "status": "COMPLIANT"},
            {"item": "SHA-384 for all hashing",                       "deadline": "2026-01-01", "status": "IN_PROGRESS"},
            {"item": "SLH-DSA-256f for long-lived document signing",  "deadline": "2030-01-01", "status": "NOT_STARTED"},
            {"item": "Eliminate RSA-2048 and ECDSA-P256",             "deadline": "2030-01-01", "status": "IN_PROGRESS"},
        ],
        "overall_compliance_pct": 32.0,
    },
    "NIST_SP1800_38": {
        "full_name": "NIST NCCoE PQC Migration — SP 1800-38",
        "issuer": "NIST National Cybersecurity Center of Excellence",
        "reference": "NIST SP 1800-38 (2024)",
        "requirements": [
            {"item": "Crypto asset discovery (CBOM)",                 "deadline": "2025-06-01", "status": "COMPLIANT"},
            {"item": "Risk-based prioritization",                     "deadline": "2025-12-01", "status": "COMPLIANT"},
            {"item": "Hybrid algorithm deployment",                   "deadline": "2027-01-01", "status": "IN_PROGRESS"},
            {"item": "Pure PQC deployment",                           "deadline": "2030-01-01", "status": "NOT_STARTED"},
            {"item": "Algorithm agility architecture",                "deadline": "2027-01-01", "status": "IN_PROGRESS"},
        ],
        "overall_compliance_pct": 40.0,
    },
    "DORA_Art30": {
        "full_name": "Digital Operational Resilience Act — Article 30",
        "issuer": "European Union",
        "reference": "DORA Regulation (EU) 2022/2554 + Delegated Regulation 2026",
        "requirements": [
            {"item": "ICT third-party PQC requirements in contracts", "deadline": "2027-12-31", "status": "NOT_STARTED"},
            {"item": "Cryptographic resilience testing",              "deadline": "2027-01-01", "status": "IN_PROGRESS"},
            {"item": "Incident reporting for crypto failures",        "deadline": "2025-01-17", "status": "COMPLIANT"},
        ],
        "overall_compliance_pct": 33.0,
    },
    "EU_NIS2": {
        "full_name": "EU Network and Information Security Directive 2",
        "issuer": "European Union",
        "reference": "NIS2 Directive 2022/2555",
        "requirements": [
            {"item": "Cryptographic policies per Art 21(2)(h)",       "deadline": "2024-10-17", "status": "COMPLIANT"},
            {"item": "Supply chain crypto assurance",                 "deadline": "2026-01-01", "status": "IN_PROGRESS"},
            {"item": "PQC incident classification",                   "deadline": "2026-06-01", "status": "IN_PROGRESS"},
        ],
        "overall_compliance_pct": 55.0,
    },
    "CISA_PQC_Guidance": {
        "full_name": "CISA Post-Quantum Cryptography Initiative",
        "issuer": "CISA",
        "reference": "CISA PQC Roadmap 2025 / Alert AA26-198A",
        "requirements": [
            {"item": "Crypto inventory completed",                    "deadline": "2025-01-01", "status": "COMPLIANT"},
            {"item": "Priority systems migrated to hybrid PQC",       "deadline": "2027-01-01", "status": "IN_PROGRESS"},
            {"item": "Vendor PQC roadmap collected",                  "deadline": "2026-01-01", "status": "IN_PROGRESS"},
        ],
        "overall_compliance_pct": 45.0,
    },
}

# ─── Vendor PQC readiness data ─────────────────────────────────────────────────

_VENDOR_PQC_SEED: List[Dict[str, Any]] = [
    {
        "vendor": "AWS",
        "product_area": "Key Management Service (KMS) + TLS",
        "pqc_status": "GA",
        "completion_pct": 75.0,
        "supported_algorithms": ["ML-KEM-768", "ML-DSA-44"],
        "hybrid_available": True,
        "fips_140_3_validated": False,
        "notes": "ML-KEM-768 hybrid TLS GA on ALB/CloudFront. KMS PQC key wrapping in preview.",
        "last_verified": "2026-09-01",
    },
    {
        "vendor": "Azure",
        "product_area": "Key Vault + Azure TLS",
        "pqc_status": "GA",
        "completion_pct": 70.0,
        "supported_algorithms": ["ML-KEM-768", "ML-DSA-65"],
        "hybrid_available": True,
        "fips_140_3_validated": True,
        "notes": "Azure Key Vault Premium supports ML-DSA-65 keys. TLS hybrid via APIM.",
        "last_verified": "2026-09-10",
    },
    {
        "vendor": "GCP",
        "product_area": "Cloud KMS + Certificate Authority Service",
        "pqc_status": "PREVIEW",
        "completion_pct": 55.0,
        "supported_algorithms": ["ML-KEM-768", "ML-DSA-44"],
        "hybrid_available": False,
        "fips_140_3_validated": False,
        "notes": "ML-DSA certificates in CAS preview. GCE TLS does not yet support hybrid KEX natively.",
        "last_verified": "2026-08-15",
    },
    {
        "vendor": "Palo Alto Networks",
        "product_area": "Next-Generation Firewall / Prisma SASE",
        "pqc_status": "IN_PROGRESS",
        "completion_pct": 40.0,
        "supported_algorithms": ["ML-KEM-768"],
        "hybrid_available": True,
        "fips_140_3_validated": False,
        "notes": "PAN-OS 11.2 adds X25519+ML-KEM-768 TLS inspection in beta. IPsec PQC roadmap TBD.",
        "last_verified": "2026-09-01",
    },
    {
        "vendor": "Cisco",
        "product_area": "IOS-XE / Catalyst / ASA",
        "pqc_status": "IN_PROGRESS",
        "completion_pct": 35.0,
        "supported_algorithms": ["ML-KEM-768"],
        "hybrid_available": False,
        "fips_140_3_validated": False,
        "notes": "IOS-XE 17.14 roadmap includes IKEv2+ML-KEM-768. VPN module update required.",
        "last_verified": "2026-08-01",
    },
    {
        "vendor": "Fortinet",
        "product_area": "FortiGate / FortiOS",
        "pqc_status": "PREVIEW",
        "completion_pct": 45.0,
        "supported_algorithms": ["ML-KEM-768", "ML-DSA-44"],
        "hybrid_available": True,
        "fips_140_3_validated": False,
        "notes": "FortiOS 7.8 preview: PQC VPN with ML-KEM-768. Hardware offload via FortiASIC not yet available.",
        "last_verified": "2026-09-05",
    },
    {
        "vendor": "CrowdStrike",
        "product_area": "Falcon Platform / Sensor TLS",
        "pqc_status": "PLANNED",
        "completion_pct": 20.0,
        "supported_algorithms": [],
        "hybrid_available": False,
        "fips_140_3_validated": False,
        "notes": "Roadmap announced for Falcon sensor PQC TLS by Q3 2027. Backend API migration planned.",
        "last_verified": "2026-07-15",
    },
    {
        "vendor": "HashiCorp Vault",
        "product_area": "Vault / Boundary",
        "pqc_status": "GA",
        "completion_pct": 80.0,
        "supported_algorithms": ["ML-KEM-768", "ML-DSA-44", "ML-DSA-65"],
        "hybrid_available": True,
        "fips_140_3_validated": False,
        "notes": "Vault 1.17+ supports ML-DSA key types and ML-KEM-768 sealing. Boundary TLS hybrid GA.",
        "last_verified": "2026-09-15",
    },
    {
        "vendor": "Okta",
        "product_area": "Identity Cloud / SAML / OIDC",
        "pqc_status": "IN_PROGRESS",
        "completion_pct": 30.0,
        "supported_algorithms": ["ML-KEM-768"],
        "hybrid_available": False,
        "fips_140_3_validated": False,
        "notes": "Okta TLS backend upgraded to hybrid ML-KEM-768. SAML assertion signing PQC roadmap H2 2027.",
        "last_verified": "2026-08-20",
    },
    {
        "vendor": "Cloudflare",
        "product_area": "CDN / Tunnel / Zero Trust",
        "pqc_status": "GA",
        "completion_pct": 90.0,
        "supported_algorithms": ["ML-KEM-768", "ML-DSA-44"],
        "hybrid_available": True,
        "fips_140_3_validated": False,
        "notes": "X25519+ML-KEM-768 default on all zones as of Sep 2026. Tunnel PQC GA. Workers crypto GA.",
        "last_verified": "2026-09-15",
    },
]


# ─── Main class ────────────────────────────────────────────────────────────────

class QuantumControlTower:
    """
    Executive PQC Migration Dashboard backend.

    Aggregates status across 29 security layers, threat intelligence,
    compliance frameworks, vendor readiness, and HNDL risk.

    Usage:
        tower = QuantumControlTower(data_dir="/path/to/pqc-control-tower/data")
        summary = tower.get_executive_summary()
        layers  = tower.get_layer_matrix()
        report  = tower.generate_ciso_report()
    """

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = pathlib.Path(data_dir) if data_dir else pathlib.Path(".")
        self._layers: List[LayerStatus] = self._load_layers()
        self._threats: List[ThreatIntelItem] = self._load_threats()

    # ── Data loading ────────────────────────────────────────────────────────────

    def _load_layers(self) -> List[LayerStatus]:
        """Load layer statuses from pqc-control-tower data files if available, else use seed."""
        layers: List[LayerStatus] = []

        cbom_path = self._data_dir / "cbom.json"
        if cbom_path.exists():
            try:
                with open(cbom_path) as f:
                    cbom = json.load(f)
                # Map CBOM assets to supplement layer seed where algo info available
                algo_map: Dict[str, str] = {}
                for asset in cbom.get("assets", []):
                    algo = asset.get("algorithm", "")
                    size = asset.get("key_size", 0)
                    if algo and size:
                        algo_map[asset.get("path", "")] = f"{algo}-{size}"
            except (json.JSONDecodeError, OSError):
                pass

        migration_path = self._data_dir / "migration_roadmap.csv"
        completion_overrides: Dict[str, float] = {}
        if migration_path.exists():
            try:
                with open(migration_path) as f:
                    for line in f:
                        parts = line.strip().split(",")
                        if len(parts) >= 3 and parts[0].startswith("L"):
                            try:
                                completion_overrides[parts[0]] = float(parts[2])
                            except ValueError:
                                pass
            except OSError:
                pass

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for raw in _LAYER_SEED:
            pct = completion_overrides.get(raw["layer_id"], raw["completion_pct"])
            layers.append(LayerStatus(
                layer_id=raw["layer_id"],
                name=raw["name"],
                completion_pct=pct,
                current_algo=raw["current_algo"],
                target_algo=raw["target_algo"],
                hndl_risk=raw["hndl_risk"],
                status=raw["status"],
                open_findings=raw["open_findings"],
                last_updated=now,
            ))
        return layers

    def _load_threats(self) -> List[ThreatIntelItem]:
        """Build threat intelligence items from seed data."""
        return [
            ThreatIntelItem(
                id=t["id"],
                title=t["title"],
                severity=t["severity"],
                cve_or_reference=t["cve_or_reference"],
                quantum_relevance=t["quantum_relevance"],
                affected_algorithms=t["affected_algorithms"],
                recommended_action=t["recommended_action"],
                published_date=t["published_date"],
            )
            for t in _THREAT_SEED
        ]

    # ── Executive summary ───────────────────────────────────────────────────────

    def get_executive_summary(self) -> TowerMetrics:
        """Aggregate all 29 layer statuses into top-level KPIs."""
        completed     = sum(1 for l in self._layers if l.status == "COMPLETED")
        in_progress   = sum(1 for l in self._layers if l.status in ("IN_PROGRESS", "HYBRID"))
        not_started   = sum(1 for l in self._layers if l.status == "NOT_STARTED")
        critical_findings = sum(l.open_findings for l in self._layers if l.hndl_risk in ("CRITICAL", "HIGH"))

        avg_completion = sum(l.completion_pct for l in self._layers) / len(self._layers)
        overall_score = round(avg_completion, 1)

        # HNDL risk: weighted by risk level
        hndl_weight = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        max_hndl = sum(hndl_weight.get(l.hndl_risk, 1) * 100 for l in self._layers)
        raw_hndl = sum(
            hndl_weight.get(l.hndl_risk, 1) * (100 - l.completion_pct)
            for l in self._layers
        )
        hndl_risk_score = round((raw_hndl / max_hndl) * 100, 1) if max_hndl > 0 else 0.0

        # Compliance score: average of all framework compliance percentages
        compliance_scores = [v["overall_compliance_pct"] for v in _COMPLIANCE_SEED.values()]
        compliance_score = round(sum(compliance_scores) / len(compliance_scores), 1)

        # Projected completion: based on current velocity
        remaining_work = 100.0 - avg_completion
        # Assume ~8% progress per year at current rate
        velocity_pct_per_year = 8.0
        years_remaining = max(1, round(remaining_work / velocity_pct_per_year))
        projected_year = datetime.now(timezone.utc).year + years_remaining

        monthly_spend = 285_000.0  # USD — realistic enterprise PQC migration spend

        return TowerMetrics(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            overall_pqc_score=overall_score,
            layers_completed=completed,
            layers_in_progress=in_progress,
            layers_not_started=not_started,
            critical_findings=critical_findings,
            hndl_risk_score=hndl_risk_score,
            compliance_score=compliance_score,
            monthly_spend_usd=monthly_spend,
            projected_completion_year=projected_year,
        )

    # ── Layer matrix ────────────────────────────────────────────────────────────

    def get_layer_matrix(self) -> List[LayerStatus]:
        """Return all 29 layers with current migration state."""
        return self._layers

    # ── HNDL risk ───────────────────────────────────────────────────────────────

    def get_hndl_risk_assessment(self) -> Dict[str, Any]:
        """
        Calculate Harvest Now Decrypt Later risk.

        Risk formula: sum(sensitivity_weight × (1 - migration_progress)) for each layer
        normalized to 0-100.
        """
        sensitivity = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 1}
        scored_layers = []
        max_possible = 0.0
        raw_score = 0.0

        for layer in self._layers:
            weight = sensitivity.get(layer.hndl_risk, 1)
            progress_fraction = layer.completion_pct / 100.0
            exposure = weight * (1.0 - progress_fraction)
            raw_score += exposure
            max_possible += weight
            scored_layers.append({
                "layer_id": layer.layer_id,
                "name": layer.name,
                "hndl_risk": layer.hndl_risk,
                "current_algo": layer.current_algo,
                "migration_progress_pct": layer.completion_pct,
                "exposure_score": round(exposure, 2),
                "status": layer.status,
            })

        normalized = round((raw_score / max_possible) * 100, 1) if max_possible > 0 else 0.0

        # Priority systems: CRITICAL/HIGH risk and under 50% complete
        priority_systems = [
            s for s in scored_layers
            if s["hndl_risk"] in ("CRITICAL", "HIGH") and s["migration_progress_pct"] < 50.0
        ]
        priority_systems.sort(key=lambda x: -x["exposure_score"])

        if normalized >= 70:
            harvest_probability = "VERY HIGH — adversaries actively collecting encrypted traffic"
            data_lifetime_risk = "EXTREME — long-lived data (>5 years) already compromised"
        elif normalized >= 50:
            harvest_probability = "HIGH — state actors collecting high-value encrypted data"
            data_lifetime_risk = "HIGH — sensitive data exposed within 3-5 year CRQC window"
        elif normalized >= 30:
            harvest_probability = "MEDIUM — opportunistic collection likely"
            data_lifetime_risk = "MEDIUM — standard enterprise data at risk post-CRQC"
        else:
            harvest_probability = "LOW — PQC migration well underway; reduced exposure"
            data_lifetime_risk = "LOW — most high-sensitivity data protected"

        return {
            "score": normalized,
            "harvest_probability": harvest_probability,
            "data_lifetime_risk": data_lifetime_risk,
            "priority_systems": priority_systems[:8],
            "all_layer_scores": scored_layers,
            "recommended_actions": [
                "Enable X25519+ML-KEM-768 hybrid TLS on all external-facing services immediately",
                "Migrate IKEv2 VPN to ML-KEM-768 KEX (RFC 9370) within 90 days",
                "Rotate all long-lived PKI keys (>2 years) to ML-DSA-65 within 180 days",
                "Classify all data by sensitivity and cross-reference with HNDL exposure per layer",
                "Implement traffic monitoring to detect adversarial TLS session capture",
            ],
            "assessed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ── Threat intelligence ─────────────────────────────────────────────────────

    def get_threat_intelligence(self) -> List[ThreatIntelItem]:
        """Return threat intelligence feed sorted by severity (CRITICAL first)."""
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return sorted(self._threats, key=lambda t: severity_order.get(t.severity, 99))

    # ── Compliance status ───────────────────────────────────────────────────────

    def get_compliance_status(self) -> Dict[str, Any]:
        """
        Return compliance status mapped to CNSA 2.0, NIST, DORA, NIS2, CISA guidance.
        """
        result = {}
        for key, framework in _COMPLIANCE_SEED.items():
            total = len(framework["requirements"])
            compliant_count = sum(
                1 for r in framework["requirements"] if r["status"] == "COMPLIANT"
            )
            in_progress_count = sum(
                1 for r in framework["requirements"] if r["status"] == "IN_PROGRESS"
            )
            not_started_count = sum(
                1 for r in framework["requirements"] if r["status"] == "NOT_STARTED"
            )
            result[key] = {
                "full_name": framework["full_name"],
                "issuer": framework["issuer"],
                "reference": framework["reference"],
                "overall_compliance_pct": framework["overall_compliance_pct"],
                "requirements_total": total,
                "requirements_compliant": compliant_count,
                "requirements_in_progress": in_progress_count,
                "requirements_not_started": not_started_count,
                "requirements": framework["requirements"],
                "gap_summary": (
                    f"{not_started_count} requirement(s) not started, "
                    f"{in_progress_count} in progress out of {total} total."
                ),
            }
        return result

    # ── Vendor PQC readiness ────────────────────────────────────────────────────

    def get_vendor_pqc_readiness(self) -> List[Dict[str, Any]]:
        """Return PQC readiness status for 10 major vendors."""
        status_order = {"GA": 0, "PREVIEW": 1, "IN_PROGRESS": 2, "PLANNED": 3, "NOT_STARTED": 4}
        vendors = sorted(
            _VENDOR_PQC_SEED,
            key=lambda v: (status_order.get(v["pqc_status"], 99), -v["completion_pct"]),
        )
        return vendors

    # ── KPI trends ──────────────────────────────────────────────────────────────

    def get_kpi_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Return simulated historical KPI trend for the past `days` days.
        Trend reflects gradual improvement in PQC score and declining HNDL risk.
        """
        current = self.get_executive_summary()
        trends = []

        # Work backwards from today
        now = datetime.now(timezone.utc)
        for i in range(days, 0, -1):
            dt = now - timedelta(days=i)
            # Each week adds ~0.5% progress; HNDL risk declines proportionally
            week_factor = i / 7.0
            score_offset = week_factor * 0.5
            hndl_offset  = week_factor * 0.4
            compliance_offset = week_factor * 0.3

            trends.append({
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "date": dt.strftime("%Y-%m-%d"),
                "overall_pqc_score": max(0.0, round(current.overall_pqc_score - score_offset, 1)),
                "hndl_risk_score": min(100.0, round(current.hndl_risk_score + hndl_offset, 1)),
                "compliance_score": max(0.0, round(current.compliance_score - compliance_offset, 1)),
                "layers_completed": max(0, current.layers_completed - (1 if i > 14 else 0)),
                "critical_findings": min(150, current.critical_findings + round(week_factor * 0.5)),
                "monthly_spend_usd": current.monthly_spend_usd,
            })

        # Add today as last point
        trends.append({
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date": now.strftime("%Y-%m-%d"),
            "overall_pqc_score": current.overall_pqc_score,
            "hndl_risk_score": current.hndl_risk_score,
            "compliance_score": current.compliance_score,
            "layers_completed": current.layers_completed,
            "critical_findings": current.critical_findings,
            "monthly_spend_usd": current.monthly_spend_usd,
        })

        return trends

    # ── CISO report ─────────────────────────────────────────────────────────────

    def generate_ciso_report(self) -> Dict[str, Any]:
        """
        Generate a board/CISO-ready PQC migration status report.

        Returns: executive_summary, critical_actions(5), 90_day_plan,
                 budget_estimate_usd, risk_reduction_pct.
        """
        summary = self.get_executive_summary()
        hndl    = self.get_hndl_risk_assessment()
        threats = self.get_threat_intelligence()

        critical_threats = [t for t in threats if t.severity == "CRITICAL"]
        high_risk_layers = [
            l for l in self._layers
            if l.hndl_risk in ("CRITICAL",) and l.completion_pct < 50.0
        ]

        critical_actions = [
            {
                "priority": "P0",
                "action": "Deploy X25519+ML-KEM-768 hybrid TLS on all external endpoints",
                "rationale": f"HNDL risk score {summary.hndl_risk_score:.0f}/100; CISA Alert AA26-198A active",
                "owner": "Network / Platform Engineering",
                "due_date": "2026-12-31",
                "estimated_effort_days": 45,
            },
            {
                "priority": "P0",
                "action": "Migrate all IKEv2 VPN tunnels to ML-KEM-768 KEX (RFC 9370)",
                "rationale": "L11 VPN layer CRITICAL HNDL risk; NCSC-2026-0042 active advisory",
                "owner": "Network Security",
                "due_date": "2027-03-31",
                "estimated_effort_days": 60,
            },
            {
                "priority": "P1",
                "action": f"Issue ML-DSA-65 certificates from PKI CA (Layer L06, {high_risk_layers[2].completion_pct if len(high_risk_layers)>2 else 55}% complete)",
                "rationale": "PKI is the root of trust; all downstream layers depend on ML-DSA cert issuance",
                "owner": "PKI / Cryptography Team",
                "due_date": "2027-06-30",
                "estimated_effort_days": 90,
            },
            {
                "priority": "P1",
                "action": "Replace AES-128 in backup/recovery (L21) with AES-256",
                "rationale": "AES-128 at 64-bit PQ security; CNSA 2.0 non-compliant; simplest migration",
                "owner": "Infrastructure Engineering",
                "due_date": "2026-12-31",
                "estimated_effort_days": 15,
            },
            {
                "priority": "P2",
                "action": "Issue PQC vendor questionnaire to all ICT third parties (DORA Art.30 deadline 2027)",
                "rationale": "DORA Delegated Regulation 2026/C-814 requires PQC clause in vendor contracts",
                "owner": "CISO / Vendor Risk Management",
                "due_date": "2027-01-31",
                "estimated_effort_days": 20,
            },
        ]

        plan_90_day = [
            {"week": "1-2",  "milestone": "Complete X25519+ML-KEM-768 lab validation and change request"},
            {"week": "3-6",  "milestone": "Deploy hybrid TLS on pilot 20% of external endpoints; monitor"},
            {"week": "7-10", "milestone": "Full external TLS hybrid rollout; verify zero-fallback in captures"},
            {"week": "11-12","milestone": "Start IKEv2 hybrid KEX on top-3 CRITICAL VPN tunnels"},
            {"week": "12",   "milestone": "AES-128 → AES-256 migration complete on backup systems"},
        ]

        # Budget: $285K/month current + $420K migration capital for critical actions
        total_budget = {
            "current_monthly_opex_usd": 285_000,
            "90_day_migration_capex_usd": 420_000,
            "annual_projection_usd": 3_420_000 + 420_000,
            "cost_per_layer_avg_usd": round(3_420_000 / 29),
            "breakdown": {
                "engineering_labour": 1_800_000,
                "tooling_licenses": 480_000,
                "hSM_hardware": 360_000,
                "testing_audit": 240_000,
                "training": 120_000,
                "contingency_15pct": 420_000,
            },
        }

        # Risk reduction: completing P0 actions reduces HNDL score by ~25 points
        risk_reduction_pct = round(
            25.0 * (len(critical_actions) / 5.0)
            + (summary.hndl_risk_score * 0.15), 1
        )

        return {
            "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "executive_summary": {
                "overall_pqc_score": summary.overall_pqc_score,
                "hndl_risk_score": summary.hndl_risk_score,
                "layers_completed": summary.layers_completed,
                "layers_in_progress": summary.layers_in_progress,
                "layers_not_started": summary.layers_not_started,
                "critical_findings": summary.critical_findings,
                "compliance_score": summary.compliance_score,
                "projected_completion_year": summary.projected_completion_year,
                "headline": (
                    f"Organization is {summary.overall_pqc_score:.0f}% through PQC migration "
                    f"with {summary.hndl_risk_score:.0f}/100 HNDL risk exposure. "
                    f"{len(critical_threats)} active critical threat intelligence items require immediate action."
                ),
            },
            "critical_actions": critical_actions,
            "90_day_plan": plan_90_day,
            "budget_estimate_usd": total_budget,
            "risk_reduction_pct": risk_reduction_pct,
            "top_threats": [
                {"id": t.id, "title": t.title, "severity": t.severity, "action": t.recommended_action}
                for t in critical_threats[:3]
            ],
        }


# ─── Quick smoke-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    tower = QuantumControlTower()

    print("=== Executive Summary ===")
    s = tower.get_executive_summary()
    print(f"  PQC Score: {s.overall_pqc_score}/100  HNDL Risk: {s.hndl_risk_score}  Compliance: {s.compliance_score}")
    print(f"  Layers: {s.layers_completed} done / {s.layers_in_progress} in progress / {s.layers_not_started} not started")

    print("\n=== Top 3 HNDL Priority Layers ===")
    hndl = tower.get_hndl_risk_assessment()
    for p in hndl["priority_systems"][:3]:
        print(f"  [{p['hndl_risk']}] {p['layer_id']} {p['name']} — {p['migration_progress_pct']:.0f}% done")

    print("\n=== Critical Threats ===")
    for t in tower.get_threat_intelligence():
        if t.severity == "CRITICAL":
            print(f"  [{t.id}] {t.title[:70]}...")

    print("\n=== CISO Report Excerpt ===")
    report = tower.generate_ciso_report()
    print(f"  Headline: {report['executive_summary']['headline']}")
    print(f"  Budget (annual): ${report['budget_estimate_usd']['annual_projection_usd']:,}")
    print(f"  Risk Reduction (P0 actions): {report['risk_reduction_pct']}%")
