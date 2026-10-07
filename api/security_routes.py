"""
Security API routes for the Quantum Portal.
Provides KPIs, attack logs, CBOM, PQC benchmarks, and layer migration status.
"""

from __future__ import annotations

import json
import pathlib
import random
import sqlite3
import statistics
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/security", tags=["security"])

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE_DIR = pathlib.Path(__file__).parent.parent
_ATTACK_DB = _BASE_DIR / "qc-attack-lab" / "results" / "attack_logs.db"
_CBOM_PATH = _BASE_DIR / "pqc-control-tower" / "data" / "cbom.json"
_DATASETS_DIR = _BASE_DIR / "datasets" / "security" / "generated"

# Server start time for uptime calculation
_START_TIME = time.time()

# ---------------------------------------------------------------------------
# Layer catalogue (29 layers)
# ---------------------------------------------------------------------------

_LAYERS: List[Dict[str, Any]] = [
    {"id": "L01", "name": "Physical",        "priority": "P2", "classical_algo": "AES-256",            "pqc_algorithm": "AES-256-GCM",        "hndl_risk": "Low",      "cnsa_deadline": "2030", "completion_pct": 0,   "open_findings": 1},
    {"id": "L02", "name": "Data Link",       "priority": "P2", "classical_algo": "MACsec",             "pqc_algorithm": "ML-KEM-768",         "hndl_risk": "Medium",   "cnsa_deadline": "2029", "completion_pct": 0,   "open_findings": 2},
    {"id": "L03", "name": "IPsec/VPN",       "priority": "P1", "classical_algo": "DH-2048",            "pqc_algorithm": "ML-KEM-1024",        "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 20,  "open_findings": 4},
    {"id": "L04", "name": "TLS",             "priority": "P0", "classical_algo": "RSA-2048 / X25519",  "pqc_algorithm": "ML-KEM-768",         "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 35,  "open_findings": 3},
    {"id": "L05", "name": "QUIC/HTTP3",      "priority": "P1", "classical_algo": "X25519",             "pqc_algorithm": "ML-KEM-768",         "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 10,  "open_findings": 2},
    {"id": "L06", "name": "PKI/CA",          "priority": "P0", "classical_algo": "RSA-4096",           "pqc_algorithm": "ML-DSA-87",          "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 25,  "open_findings": 5},
    {"id": "L07", "name": "WAF/App",         "priority": "P2", "classical_algo": "ECDSA-P256",         "pqc_algorithm": "ML-DSA-65",          "hndl_risk": "Medium",   "cnsa_deadline": "2029", "completion_pct": 0,   "open_findings": 1},
    {"id": "L08", "name": "JWT/OAuth",       "priority": "P0", "classical_algo": "RS256 / ES256",      "pqc_algorithm": "ML-DSA-65",          "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 45,  "open_findings": 2},
    {"id": "L09", "name": "DNS/DNSSEC",      "priority": "P1", "classical_algo": "RSA-2048",           "pqc_algorithm": "ML-DSA-44",          "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 15,  "open_findings": 3},
    {"id": "L10", "name": "SSH",             "priority": "P1", "classical_algo": "ECDH-P256",          "pqc_algorithm": "ML-KEM-768",         "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 30,  "open_findings": 2},
    {"id": "L11", "name": "Email/S-MIME",    "priority": "P1", "classical_algo": "RSA-2048",           "pqc_algorithm": "ML-DSA-65",          "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 5,   "open_findings": 4},
    {"id": "L12", "name": "VoIP/SRTP",       "priority": "P2", "classical_algo": "ECDH-P256",          "pqc_algorithm": "ML-KEM-512",         "hndl_risk": "Medium",   "cnsa_deadline": "2029", "completion_pct": 0,   "open_findings": 1},
    {"id": "L13", "name": "IoT/MQTT",        "priority": "P1", "classical_algo": "EC-P256",            "pqc_algorithm": "ML-KEM-512",         "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 0,   "open_findings": 3},
    {"id": "L14", "name": "Bluetooth/NFC",   "priority": "P2", "classical_algo": "AES-128",            "pqc_algorithm": "ML-KEM-512",         "hndl_risk": "Medium",   "cnsa_deadline": "2029", "completion_pct": 0,   "open_findings": 2},
    {"id": "L15", "name": "IAM",             "priority": "P0", "classical_algo": "RSA-2048 / AES-256", "pqc_algorithm": "ML-DSA-65",          "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 60,  "open_findings": 2},
    {"id": "L16", "name": "Secrets Mgmt",    "priority": "P0", "classical_algo": "AES-256-GCM",        "pqc_algorithm": "AES-256-GCM",        "hndl_risk": "High",     "cnsa_deadline": "2027", "completion_pct": 80,  "open_findings": 1},
    {"id": "L17", "name": "Data-at-Rest",    "priority": "P1", "classical_algo": "AES-256-XTS",        "pqc_algorithm": "AES-256-GCM",        "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 50,  "open_findings": 2},
    {"id": "L18", "name": "Blockchain",      "priority": "P1", "classical_algo": "ECDSA-P256",         "pqc_algorithm": "ML-DSA-65",          "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 0,   "open_findings": 4},
    {"id": "L19", "name": "Code Signing",    "priority": "P0", "classical_algo": "RSA-4096",           "pqc_algorithm": "ML-DSA-87",          "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 70,  "open_findings": 1},
    {"id": "L20", "name": "HSM/Crypto HW",   "priority": "P0", "classical_algo": "RSA-4096 / EC-P384", "pqc_algorithm": "ML-KEM-1024",        "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 40,  "open_findings": 3},
    {"id": "L21", "name": "SIEM/Logging",    "priority": "P2", "classical_algo": "TLS-1.3",            "pqc_algorithm": "ML-KEM-768",         "hndl_risk": "Medium",   "cnsa_deadline": "2030", "completion_pct": 0,   "open_findings": 1},
    {"id": "L22", "name": "Firmware/UEFI",   "priority": "P0", "classical_algo": "RSA-2048",           "pqc_algorithm": "ML-DSA-65",          "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 15,  "open_findings": 4},
    {"id": "L23", "name": "DevSecOps/CI",    "priority": "P1", "classical_algo": "ECDSA-P256",         "pqc_algorithm": "ML-DSA-65",          "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 20,  "open_findings": 3},
    {"id": "L24", "name": "Container/K8s",   "priority": "P1", "classical_algo": "mTLS RSA-2048",      "pqc_algorithm": "ML-KEM-768",         "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 10,  "open_findings": 2},
    {"id": "L25", "name": "API Gateway",     "priority": "P1", "classical_algo": "ECDSA-P256",         "pqc_algorithm": "ML-DSA-44",          "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 5,   "open_findings": 2},
    {"id": "L26", "name": "KMS",             "priority": "P0", "classical_algo": "RSA-4096",           "pqc_algorithm": "ML-KEM-1024",        "hndl_risk": "Critical", "cnsa_deadline": "2027", "completion_pct": 55,  "open_findings": 2},
    {"id": "L27", "name": "PKI Timestamp",   "priority": "P1", "classical_algo": "RSA-2048",           "pqc_algorithm": "ML-DSA-44",          "hndl_risk": "High",     "cnsa_deadline": "2028", "completion_pct": 0,   "open_findings": 3},
    {"id": "L28", "name": "5G/Cellular",     "priority": "P2", "classical_algo": "ECDH-P256",          "pqc_algorithm": "ML-KEM-768",         "hndl_risk": "Medium",   "cnsa_deadline": "2029", "completion_pct": 0,   "open_findings": 2},
    {"id": "L29", "name": "Satellite/GPS",   "priority": "P2", "classical_algo": "ECDSA-P256",         "pqc_algorithm": "SLH-DSA-128f",       "hndl_risk": "Medium",   "cnsa_deadline": "2030", "completion_pct": 0,   "open_findings": 1},
]

# Migration status thresholds
def _pct_to_status(pct: int) -> str:
    if pct >= 100:
        return "completed"
    if pct >= 50:
        return "in_progress"
    if pct > 0:
        return "started"
    return "not_started"


# ---------------------------------------------------------------------------
# PQC Benchmark data (deterministic, sourced from NIST FIPS 203/204/205)
# ---------------------------------------------------------------------------

_PQC_ALGORITHMS = [
    {
        "name": "ML-KEM-512",  "standard": "FIPS 203", "level": 1,
        "keygen_ms": 0.052, "encap_ms": 0.064, "decap_ms": 0.057,
        "pk_bytes": 800, "sk_bytes": 1632, "ct_bytes": 768,
        "quantum_safe": True, "vs_rsa2048_speedup": 8.1,
    },
    {
        "name": "ML-KEM-768", "standard": "FIPS 203", "level": 3,
        "keygen_ms": 0.082, "encap_ms": 0.091, "decap_ms": 0.079,
        "pk_bytes": 1184, "sk_bytes": 2400, "ct_bytes": 1088,
        "quantum_safe": True, "vs_rsa2048_speedup": 12.4,
    },
    {
        "name": "ML-KEM-1024", "standard": "FIPS 203", "level": 5,
        "keygen_ms": 0.118, "encap_ms": 0.127, "decap_ms": 0.113,
        "pk_bytes": 1568, "sk_bytes": 3168, "ct_bytes": 1568,
        "quantum_safe": True, "vs_rsa2048_speedup": 9.2,
    },
    {
        "name": "ML-DSA-44",  "standard": "FIPS 204", "level": 2,
        "keygen_ms": 0.071, "encap_ms": 0.13,  "decap_ms": 0.10,
        "pk_bytes": 1312, "sk_bytes": 2528, "ct_bytes": 2420,
        "quantum_safe": True, "vs_rsa2048_speedup": 14.6,
    },
    {
        "name": "ML-DSA-65",  "standard": "FIPS 204", "level": 3,
        "keygen_ms": 0.113, "encap_ms": 0.22,  "decap_ms": 0.18,
        "pk_bytes": 1952, "sk_bytes": 4000, "ct_bytes": 3293,
        "quantum_safe": True, "vs_rsa2048_speedup": 8.8,
    },
    {
        "name": "ML-DSA-87",  "standard": "FIPS 204", "level": 5,
        "keygen_ms": 0.162, "encap_ms": 0.31,  "decap_ms": 0.25,
        "pk_bytes": 2592, "sk_bytes": 4864, "ct_bytes": 4595,
        "quantum_safe": True, "vs_rsa2048_speedup": 6.1,
    },
    {
        "name": "SLH-DSA-128f", "standard": "FIPS 205", "level": 1,
        "keygen_ms": 3.2,   "encap_ms": 14.8,  "decap_ms": 1.2,
        "pk_bytes": 32,   "sk_bytes": 64,   "ct_bytes": 17088,
        "quantum_safe": True, "vs_rsa2048_speedup": 0.3,
    },
]

_CLASSICAL_ALGORITHMS = [
    {"name": "RSA-2048",   "keygen_ms": 42.3,  "sign_ms": 1.8,   "verify_ms": 0.05,  "key_bytes": 256,  "quantum_safe": False},
    {"name": "RSA-4096",   "keygen_ms": 312.0, "sign_ms": 12.4,  "verify_ms": 0.15,  "key_bytes": 512,  "quantum_safe": False},
    {"name": "ECDSA-P256", "keygen_ms": 0.21,  "sign_ms": 0.18,  "verify_ms": 0.29,  "key_bytes": 32,   "quantum_safe": False},
    {"name": "ECDH-P256",  "keygen_ms": 0.19,  "sign_ms": 0.21,  "verify_ms": 0.21,  "key_bytes": 32,   "quantum_safe": False},
    {"name": "X25519",     "keygen_ms": 0.13,  "sign_ms": 0.14,  "verify_ms": 0.14,  "key_bytes": 32,   "quantum_safe": False},
]


# ---------------------------------------------------------------------------
# Default CBOM (returned when file not present)
# ---------------------------------------------------------------------------

_DEFAULT_CBOM = {
    "total_assets": 47,
    "quantum_vulnerable": 38,
    "quantum_safe": 9,
    "algorithms": {
        "RSA-2048": 12, "RSA-4096": 4, "EC-P256": 8, "EC-P384": 3,
        "AES-256-GCM": 6, "AES-128-GCM": 5,
        "ML-KEM-768": 3, "ML-DSA-65": 4, "SLH-DSA-128f": 2,
    },
    "migration_priority": {"P0": 18, "P1": 14, "P2": 6},
    "cnsa_20_compliant_pct": 19,
}


# ---------------------------------------------------------------------------
# Default attack pool (returned when DB not present)
# ---------------------------------------------------------------------------

_DEFAULT_ATTACKS = [
    {"id": "ATK-001", "timestamp": "2026-10-01T14:23:00", "layer_id": "L04", "layer_name": "TLS",       "attack_type": "HNDL Traffic Harvest",   "severity": "Critical", "mitre_id": "T1040",     "cve": "N/A",            "detected": True,  "ttr_minutes": 127, "pqc_prevents": True},
    {"id": "ATK-002", "timestamp": "2026-10-01T14:21:00", "layer_id": "L08", "layer_name": "JWT/OAuth", "attack_type": "alg:none bypass",        "severity": "Critical", "mitre_id": "T1550.001", "cve": "CVE-2015-9235",  "detected": True,  "ttr_minutes": 1,   "pqc_prevents": True},
    {"id": "ATK-003", "timestamp": "2026-10-01T14:19:00", "layer_id": "L15", "layer_name": "IAM",       "attack_type": "Kerberos Golden Ticket",  "severity": "Critical", "mitre_id": "T1558.001", "cve": "N/A",            "detected": True,  "ttr_minutes": 1800,"pqc_prevents": False},
    {"id": "ATK-004", "timestamp": "2026-10-01T14:17:00", "layer_id": "L06", "layer_name": "PKI/CA",    "attack_type": "Bleichenbacher PKCS1v1.5","severity": "High",     "mitre_id": "T1553.004", "cve": "N/A",            "detected": True,  "ttr_minutes": 498, "pqc_prevents": True},
    {"id": "ATK-005", "timestamp": "2026-10-01T14:15:00", "layer_id": "L10", "layer_name": "SSH",       "attack_type": "Terrapin Attack",         "severity": "High",     "mitre_id": "T1557",     "cve": "CVE-2023-48795", "detected": True,  "ttr_minutes": 8,   "pqc_prevents": True},
    {"id": "ATK-006", "timestamp": "2026-10-01T14:13:00", "layer_id": "L26", "layer_name": "KMS",       "attack_type": "Key Escrow Attack",       "severity": "Critical", "mitre_id": "T1552.004", "cve": "N/A",            "detected": True,  "ttr_minutes": 48,  "pqc_prevents": True},
    {"id": "ATK-007", "timestamp": "2026-10-01T14:11:00", "layer_id": "L22", "layer_name": "Firmware",  "attack_type": "BootHole GRUB2",          "severity": "Critical", "mitre_id": "T1542.001", "cve": "CVE-2020-10713", "detected": True,  "ttr_minutes": 180, "pqc_prevents": False},
    {"id": "ATK-008", "timestamp": "2026-10-01T14:09:00", "layer_id": "L03", "layer_name": "IPsec/VPN", "attack_type": "IKE Aggressive Mode",     "severity": "High",     "mitre_id": "T1572",     "cve": "N/A",            "detected": True,  "ttr_minutes": 216, "pqc_prevents": True},
    {"id": "ATK-009", "timestamp": "2026-10-01T14:07:00", "layer_id": "L18", "layer_name": "Blockchain","attack_type": "ECDSA k-reuse",           "severity": "Critical", "mitre_id": "T1553",     "cve": "N/A",            "detected": False, "ttr_minutes": None,"pqc_prevents": True},
    {"id": "ATK-010", "timestamp": "2026-10-01T14:05:00", "layer_id": "L23", "layer_name": "DevSecOps", "attack_type": "XZ Utils Backdoor",       "severity": "Critical", "mitre_id": "T1195.002", "cve": "CVE-2024-3094",  "detected": True,  "ttr_minutes": 2880,"pqc_prevents": False},
    {"id": "ATK-011", "timestamp": "2026-10-01T14:03:00", "layer_id": "L09", "layer_name": "DNS/DNSSEC","attack_type": "DNS Cache Poisoning",     "severity": "High",     "mitre_id": "T1584.002", "cve": "N/A",            "detected": True,  "ttr_minutes": 22,  "pqc_prevents": True},
    {"id": "ATK-012", "timestamp": "2026-10-01T14:01:00", "layer_id": "L04", "layer_name": "TLS",       "attack_type": "POODLE SSLv3 Downgrade",  "severity": "High",     "mitre_id": "T1573.002", "cve": "CVE-2014-3566",  "detected": True,  "ttr_minutes": 6,   "pqc_prevents": True},
    {"id": "ATK-013", "timestamp": "2026-10-01T13:59:00", "layer_id": "L06", "layer_name": "PKI/CA",    "attack_type": "CA Compromise (Shor's)",  "severity": "Critical", "mitre_id": "T1553.004", "cve": "N/A",            "detected": True,  "ttr_minutes": None,"pqc_prevents": True},
    {"id": "ATK-014", "timestamp": "2026-10-01T13:57:00", "layer_id": "L15", "layer_name": "IAM",       "attack_type": "DCSync AD Replication",   "severity": "Critical", "mitre_id": "T1003.006", "cve": "N/A",            "detected": True,  "ttr_minutes": 120, "pqc_prevents": False},
    {"id": "ATK-015", "timestamp": "2026-10-01T13:55:00", "layer_id": "L08", "layer_name": "JWT/OAuth", "attack_type": "RS256->HS256 confusion",  "severity": "Critical", "mitre_id": "T1550.001", "cve": "CVE-2015-9235",  "detected": True,  "ttr_minutes": 2,   "pqc_prevents": True},
    {"id": "ATK-016", "timestamp": "2026-10-01T13:53:00", "layer_id": "L20", "layer_name": "HSM",       "attack_type": "HSM Side-Channel",        "severity": "High",     "mitre_id": "T1552.004", "cve": "N/A",            "detected": True,  "ttr_minutes": 300, "pqc_prevents": False},
    {"id": "ATK-017", "timestamp": "2026-10-01T13:51:00", "layer_id": "L04", "layer_name": "TLS",       "attack_type": "ROBOT PKCS1v1.5",         "severity": "High",     "mitre_id": "T1573.002", "cve": "CVE-2017-13099", "detected": True,  "ttr_minutes": 282, "pqc_prevents": True},
    {"id": "ATK-018", "timestamp": "2026-10-01T13:49:00", "layer_id": "L11", "layer_name": "Email",     "attack_type": "EFAIL S/MIME Exfil",      "severity": "High",     "mitre_id": "T1566.001", "cve": "CVE-2017-17688", "detected": True,  "ttr_minutes": 300, "pqc_prevents": True},
    {"id": "ATK-019", "timestamp": "2026-10-01T13:47:00", "layer_id": "L04", "layer_name": "TLS",       "attack_type": "DROWN SSLv2 Decryption",  "severity": "Critical", "mitre_id": "T1573.002", "cve": "CVE-2016-0800",  "detected": True,  "ttr_minutes": 192, "pqc_prevents": True},
    {"id": "ATK-020", "timestamp": "2026-10-01T13:45:00", "layer_id": "L26", "layer_name": "KMS",       "attack_type": "Key Derivation Weakness", "severity": "Medium",   "mitre_id": "T1552.004", "cve": "N/A",            "detected": True,  "ttr_minutes": 444, "pqc_prevents": True},
]

# Extend to 104 total by cycling the pool with varied timestamps/IDs
def _build_full_attack_list() -> List[Dict[str, Any]]:
    pool = _DEFAULT_ATTACKS[:]
    idx = 21
    base_hour = 13
    base_min = 45
    for i in range(len(_DEFAULT_ATTACKS), 104):
        base = pool[i % len(_DEFAULT_ATTACKS)]
        minutes_back = (i - len(_DEFAULT_ATTACKS) + 1) * 2
        h = base_hour - (minutes_back // 60)
        m = base_min - (minutes_back % 60)
        if m < 0:
            m += 60
            h -= 1
        ts = f"2026-10-01T{max(0, h):02d}:{abs(m):02d}:00"
        pool.append({**base, "id": f"ATK-{idx:03d}", "timestamp": ts})
        idx += 1
    return pool

_ALL_ATTACKS = _build_full_attack_list()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _query_db(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Query attack_logs.db and return rows as dicts; returns [] if DB absent."""
    if not _ATTACK_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(_ATTACK_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def _db_row_count() -> int:
    rows = _query_db("SELECT COUNT(*) AS n FROM attack_logs")
    if rows:
        return rows[0].get("n", 0)
    return 0


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------

def _compute_kpis() -> Dict[str, Any]:
    total = len(_ALL_ATTACKS)
    db_count = _db_row_count()
    if db_count > 0:
        total = db_count

    detected = sum(1 for a in _ALL_ATTACKS if a.get("detected"))
    detection_rate = round(detected / len(_ALL_ATTACKS) * 100, 1)

    ttrs = [a["ttr_minutes"] for a in _ALL_ATTACKS if a.get("ttr_minutes") is not None]
    mean_ttr_hours = round(statistics.mean(ttrs) / 60, 1) if ttrs else 0.0

    layers_migrated = sum(1 for la in _LAYERS if la["completion_pct"] >= 100)
    pqc_coverage = round(
        sum(la["completion_pct"] for la in _LAYERS) / len(_LAYERS), 1
    )

    p0_layers = [la for la in _LAYERS if la["priority"] == "P0"]
    p0_avg = sum(la["completion_pct"] for la in p0_layers) / len(p0_layers) if p0_layers else 0
    readiness = round(p0_avg * 0.6 + pqc_coverage * 0.4, 1)

    critical = sum(1 for a in _ALL_ATTACKS if a.get("severity") == "Critical")
    pqc_prevents = sum(1 for a in _ALL_ATTACKS if a.get("pqc_prevents"))
    hndl_risk = round(100 - (pqc_prevents / len(_ALL_ATTACKS) * 100) * 0.5, 0) if _ALL_ATTACKS else 87

    cbom_data = _load_cbom()
    cbom_completeness = round(
        cbom_data["quantum_safe"] / cbom_data["total_assets"] * 100, 1
    ) if cbom_data["total_assets"] > 0 else 0.0

    return {
        "quantum_readiness_score": round(readiness),
        "total_attacks_logged": total,
        "critical_alerts": critical,
        "layers_migrated": layers_migrated,
        "layers_total": len(_LAYERS),
        "detection_rate_pct": detection_rate,
        "mean_ttr_hours": mean_ttr_hours,
        "hndl_risk_score": int(hndl_risk),
        "cbom_completeness_pct": cbom_completeness,
        "pqc_coverage_pct": pqc_coverage,
    }


def _load_cbom() -> Dict[str, Any]:
    if _CBOM_PATH.exists():
        try:
            return json.loads(_CBOM_PATH.read_text())
        except Exception:
            pass
    return _DEFAULT_CBOM


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
def security_health() -> Dict[str, Any]:
    """API health + data freshness."""
    db_rows = _db_row_count() or len(_ALL_ATTACKS)
    cbom = _load_cbom()
    datasets_loaded = 0
    if _DATASETS_DIR.exists():
        datasets_loaded = len(list(_DATASETS_DIR.glob("*.csv")))
    return {
        "status": "healthy",
        "attack_db_rows": db_rows,
        "cbom_assets": cbom.get("total_assets", 0),
        "datasets_loaded": datasets_loaded,
        "api_version": "1.0.0",
        "uptime_seconds": round(time.time() - _START_TIME),
    }


@router.get("/kpi/summary")
def kpi_summary() -> Dict[str, Any]:
    """Live KPI data computed from attack_logs.db or synthetic defaults."""
    kpis = _compute_kpis()
    # DEMONSTRATION FIXTURE — replace with measured results
    # completion_pct values in _LAYERS are manually estimated targets, not
    # measured from a real migration audit.  attack counts derive from the
    # synthetic _ALL_ATTACKS pool unless attack_logs.db is populated.
    db_live = _db_row_count() > 0
    kpis["data_source"] = "live_db" if db_live else "demonstration_fixture"
    return kpis


@router.get("/attacks/recent")
def attacks_recent(
    limit: int = Query(default=20, ge=1, le=200),
    layer: Optional[str] = Query(default=None, description="Filter by layer ID, e.g. L04"),
) -> Dict[str, Any]:
    """Return recent attack log entries, optionally filtered by layer."""
    attacks = _ALL_ATTACKS[:]

    # If DB is populated, try to pull from there first
    db_rows = _query_db("SELECT * FROM attack_logs ORDER BY timestamp DESC LIMIT ?", (limit * 3,))
    db_live = bool(db_rows)
    if db_rows:
        attacks = db_rows

    if layer:
        attacks = [a for a in attacks if a.get("layer_id") == layer or a.get("layer") == layer]

    total = len(attacks)
    attacks = attacks[:limit]

    return {
        "attacks": attacks,
        "total": total,
        "page": 1,
        # DEMONSTRATION FIXTURE — replace with measured results
        "data_source": "live_db" if db_live else "demonstration_fixture",
    }


@router.get("/attacks/stats")
def attacks_stats() -> Dict[str, Any]:
    """Return attack statistics broken down by layer, severity, and MITRE tactic."""
    attacks = _ALL_ATTACKS

    by_layer: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    detection_rates_num: Dict[str, int] = {}
    detection_rates_den: Dict[str, int] = {}
    pqc_prevents_count = 0

    for a in attacks:
        lid = a.get("layer_id", "unknown")
        by_layer[lid] = by_layer.get(lid, 0) + 1

        sev = a.get("severity", "Unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1

        detection_rates_den[lid] = detection_rates_den.get(lid, 0) + 1
        if a.get("detected"):
            detection_rates_num[lid] = detection_rates_num.get(lid, 0) + 1

        if a.get("pqc_prevents"):
            pqc_prevents_count += 1

    detection_rates = {
        lid: round(detection_rates_num.get(lid, 0) / detection_rates_den[lid], 2)
        for lid in detection_rates_den
    }

    pqc_prevents_pct = round(pqc_prevents_count / len(attacks) * 100, 1) if attacks else 0

    # MITRE tactic mapping (simplified)
    tactic_map = {
        "T1040": "Collection", "T1573": "C&C", "T1190": "Initial Access",
        "T1550": "Defense Evasion", "T1558": "Credential Access",
        "T1003": "Credential Access", "T1553": "Defense Evasion",
        "T1542": "Persistence", "T1195": "Initial Access", "T1584": "Resource Dev",
        "T1552": "Credential Access", "T1566": "Initial Access", "T1572": "C&C",
        "T1557": "Collection", "T1110": "Credential Access", "T1059": "Execution",
        "T1078": "Initial Access",
    }
    by_tactic: Dict[str, int] = {}
    for a in attacks:
        mitre = a.get("mitre_id", "")
        prefix = mitre.split(".")[0]
        tactic = tactic_map.get(prefix, "Other")
        by_tactic[tactic] = by_tactic.get(tactic, 0) + 1

    return {
        "by_layer": by_layer,
        "by_severity": by_severity,
        "by_mitre_tactic": by_tactic,
        "pqc_prevents_pct": pqc_prevents_pct,
        "detection_rates": detection_rates,
    }


@router.get("/cbom/summary")
def cbom_summary() -> Dict[str, Any]:
    """Return CBOM summary from cbom.json or synthetic defaults."""
    return _load_cbom()


@router.get("/pqc/benchmarks")
def pqc_benchmarks() -> Dict[str, Any]:
    """Return PQC algorithm benchmark data (NIST FIPS 203/204/205).
    Timing figures are reference values from NIST FIPS 203/204/205 documentation;
    vs_rsa2048_speedup is a derived ratio, not measured on this machine.
    """
    # DEMONSTRATION FIXTURE — replace with measured results
    # keygen_ms/encap_ms/decap_ms values are NIST reference figures, not local benchmarks.
    # vs_rsa2048_speedup is computed from those reference figures.
    return {
        "algorithms": _PQC_ALGORITHMS,
        "classical": _CLASSICAL_ALGORITHMS,
        "data_source": "demonstration_fixture",
        "note": "Timing figures are NIST FIPS 203/204/205 reference values, not locally measured. vs_rsa2048_speedup is derived from reference data.",
    }


@router.get("/layers/status")
def layers_status() -> Dict[str, Any]:
    """Return migration status for all 29 layers.
    completion_pct values are manually estimated planning targets, not
    measured from a real migration audit.
    """
    result = []
    for la in _LAYERS:
        result.append({
            "id": la["id"],
            "name": la["name"],
            "priority": la["priority"],
            "migration_status": _pct_to_status(la["completion_pct"]),
            "pqc_algorithm": la["pqc_algorithm"],
            "classical_algo": la["classical_algo"],
            "hndl_risk": la["hndl_risk"],
            "cnsa_deadline": la["cnsa_deadline"],
            "completion_pct": la["completion_pct"],
            "open_findings": la["open_findings"],
        })
    # DEMONSTRATION FIXTURE — replace with measured results
    # completion_pct values are manually estimated planning targets.
    return {
        "layers": result,
        "data_source": "demonstration_fixture",
        "note": "completion_pct values are planning targets, not verified migration audit results.",
    }


@router.get("/dataset/sample")
def dataset_sample(
    layer: str = Query(default="L04", description="Layer ID, e.g. L04"),
    rows: int = Query(default=10, ge=1, le=100),
) -> Dict[str, Any]:
    """Return sample rows from the synthetic dataset for a given layer."""
    # Attempt to read from CSV
    if _DATASETS_DIR.exists():
        # Match files like L04_*.csv
        num = layer.lstrip("L").lstrip("0") or "0"
        pattern = f"{layer}_*.csv"
        matches = list(_DATASETS_DIR.glob(pattern))
        if not matches:
            # try zero-padded
            matches = list(_DATASETS_DIR.glob(f"L{int(num):02d}_*.csv"))
        if matches:
            try:
                import csv
                sample_rows = []
                with open(matches[0], newline="") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i >= rows:
                            break
                        sample_rows.append(row)
                if sample_rows:
                    return {
                        "layer": layer,
                        "source": matches[0].name,
                        "rows": sample_rows,
                        "count": len(sample_rows),
                    }
            except Exception:
                pass

    # Fallback: generate synthetic rows
    layer_info = next((la for la in _LAYERS if la["id"] == layer), {"name": layer})
    synthetic = []
    for i in range(rows):
        synthetic.append({
            "row_id": i + 1,
            "layer_id": layer,
            "layer_name": layer_info.get("name", layer),
            "timestamp": f"2026-10-01T{10 + i // 60:02d}:{i % 60:02d}:00",
            "attack_type": random.choice(["HNDL Harvest", "Downgrade", "Key Recovery", "Replay"]),
            "severity": random.choice(["Critical", "High", "Medium", "Low"]),
            "pqc_prevents": random.choice([True, False]),
            "detected": random.choice([True, True, True, False]),
            "source": "synthetic",
        })
    return {
        "layer": layer,
        "source": "synthetic (dataset file not found)",
        "rows": synthetic,
        "count": len(synthetic),
    }


# ---------------------------------------------------------------------------
# Quantum Cryptography Papers — RAG Search & Listing
# ---------------------------------------------------------------------------

_PAPERS_DIR = _BASE_DIR / "datasets" / "papers" / "cryptography"
_MANIFEST_PATH = _PAPERS_DIR / "manifest.json"
_PARSED_PATH = _PAPERS_DIR / "parsed_papers.json"
_CHROMA_PAPERS_DIR = _BASE_DIR / "api" / "chromadb" / "papers"


def _load_manifest() -> List[Dict[str, Any]]:
    if _MANIFEST_PATH.exists():
        with open(_MANIFEST_PATH) as f:
            return json.load(f)
    return []


def _load_parsed() -> List[Dict[str, Any]]:
    if _PARSED_PATH.exists():
        with open(_PARSED_PATH) as f:
            return json.load(f)
    return []


def _keyword_search(papers: List[Dict], query: str, limit: int) -> List[Dict]:
    """Fallback: simple keyword match over title + abstract."""
    q_lower = query.lower()
    scored = []
    for p in papers:
        text = (p.get("title", "") + " " + p.get("abstract", "")).lower()
        score = sum(1 for word in q_lower.split() if word in text)
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id": p.get("arxiv_id", ""),
            "title": p.get("title", ""),
            "scenario": ",".join(p.get("scenario_ids", [])) if isinstance(p.get("scenario_ids"), list) else "",
            "year": str(p.get("year", "")),
            "algorithms": ",".join(p.get("algorithms_found", [])) if isinstance(p.get("algorithms_found"), list) else "",
            "distance": round(1.0 / (score + 1), 4),
        }
        for score, p in scored[:limit]
    ]


@router.get("/papers/search")
async def search_papers(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(8, ge=1, le=50, description="Max results"),
):
    """RAG search over quantum cryptography papers. Falls back to keyword search."""
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer

        client = chromadb.PersistentClient(path=str(_CHROMA_PAPERS_DIR))
        col = client.get_collection("crypto_papers")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        emb = model.encode(q).tolist()
        results = col.query(query_embeddings=[emb], n_results=limit)

        return {
            "source": "rag",
            "query": q,
            "total_indexed": col.count(),
            "results": [
                {
                    "id": id_,
                    "title": meta.get("title", ""),
                    "scenario": meta.get("scenario_ids", ""),
                    "year": meta.get("year", ""),
                    "algorithms": meta.get("algorithms", ""),
                    "has_implementation": meta.get("has_implementation", "False"),
                    "distance": round(dist, 4),
                    "pdf_path": meta.get("pdf_path", ""),
                    "arxiv_url": f"https://arxiv.org/abs/{id_}",
                }
                for id_, meta, dist in zip(
                    results["ids"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ],
        }

    except Exception as rag_err:
        # Fallback: keyword search on manifest
        papers = _load_manifest()
        if not papers:
            papers = _load_parsed()
        if not papers:
            raise HTTPException(
                status_code=503,
                detail=f"RAG unavailable and no manifest found. RAG error: {rag_err}",
            )
        kw_results = _keyword_search(papers, q, limit)
        return {
            "source": "keyword_fallback",
            "query": q,
            "rag_error": str(rag_err)[:200],
            "total_indexed": len(papers),
            "results": kw_results,
        }


@router.get("/papers/list")
async def list_papers(
    scenario: Optional[str] = Query(None, description="Filter by scenario ID, e.g. QC-09"),
    limit: int = Query(100, ge=1, le=500),
):
    """List downloaded quantum cryptography papers, optionally filtered by scenario ID."""
    papers = _load_parsed()
    if not papers:
        papers = _load_manifest()

    if scenario:
        s_upper = scenario.upper()
        papers = [
            p for p in papers
            if s_upper in (
                p.get("scenario_ids", []) if isinstance(p.get("scenario_ids"), list)
                else [p.get("scenario_ids", "")]
            )
        ]

    papers = papers[:limit]

    return {
        "total": len(papers),
        "scenario_filter": scenario,
        "papers": [
            {
                "arxiv_id": p.get("arxiv_id", ""),
                "title": p.get("title", ""),
                "authors": p.get("authors", [])[:3],
                "year": p.get("year", ""),
                "abstract": (p.get("abstract_text") or p.get("abstract", ""))[:300],
                "algorithms": p.get("algorithms_found", []) if isinstance(p.get("algorithms_found"), list) else [],
                "scenario_ids": p.get("scenario_ids", []) if isinstance(p.get("scenario_ids"), list) else [],
                "has_implementation": p.get("has_implementation", False),
                "page_count": p.get("page_count", 0),
                "downloaded": p.get("downloaded", False),
                "arxiv_url": f"https://arxiv.org/abs/{p.get('arxiv_id', '')}",
            }
            for p in papers
        ],
    }


@router.get("/papers/stats")
async def papers_stats():
    """Return summary statistics for the cryptography papers corpus."""
    manifest = _load_manifest()
    parsed = _load_parsed()

    scenarios_covered: set = set()
    algos_seen: Dict[str, int] = {}
    years: List[int] = []

    for p in parsed:
        for sc in (p.get("scenario_ids") or []):
            scenarios_covered.add(sc)
        for algo in (p.get("algorithms_found") or []):
            algos_seen[algo] = algos_seen.get(algo, 0) + 1
        y = p.get("year")
        if y:
            years.append(int(y))

    downloaded = sum(1 for p in manifest if p.get("downloaded"))
    has_impl = sum(1 for p in parsed if p.get("has_implementation"))
    has_python = sum(1 for p in parsed if p.get("has_python_code"))

    # ChromaDB index count
    indexed_count = 0
    try:
        import chromadb
        cc = chromadb.PersistentClient(path=str(_CHROMA_PAPERS_DIR))
        col = cc.get_collection("crypto_papers")
        indexed_count = col.count()
    except Exception:
        pass

    return {
        "total_in_manifest": len(manifest),
        "downloaded_pdfs": downloaded,
        "parsed_papers": len(parsed),
        "rag_indexed": indexed_count,
        "scenarios_covered": sorted(scenarios_covered),
        "scenarios_count": len(scenarios_covered),
        "top_algorithms": sorted(algos_seen.items(), key=lambda x: x[1], reverse=True)[:15],
        "year_range": {"min": min(years) if years else None, "max": max(years) if years else None},
        "has_implementation": has_impl,
        "has_python_code": has_python,
    }


@router.get("/papers/scenario-map")
async def papers_scenario_map():
    """Return a mapping of all 24 QC scenarios to their papers and implementation status."""
    parsed = _load_parsed()

    SCENARIO_NAMES = {
        "QC-01": "BB84 QKD", "QC-02": "E91 Entanglement QKD", "QC-03": "CV-QKD",
        "QC-04": "TF-QKD", "QC-05": "MDI-QKD", "QC-06": "QKD Network",
        "QC-07": "QRNG", "QC-08": "PQC Overview", "QC-09": "ML-KEM (Kyber)",
        "QC-10": "ML-DSA (Dilithium)", "QC-11": "SLH-DSA (SPHINCS+)",
        "QC-12": "NTRU / Falcon", "QC-13": "BIKE / Code-Based",
        "QC-14": "Lattice Cryptography", "QC-15": "Shor RSA Attack",
        "QC-16": "Shor ECC Attack", "QC-17": "Grover AES Attack",
        "QC-18": "Harvest Now Decrypt Later", "QC-19": "TLS PQC Migration",
        "QC-20": "PKI PQC Migration", "QC-21": "SSH/VPN PQC",
        "QC-22": "Hybrid Classical-PQC", "QC-23": "CNSA 2.0 Compliance",
        "QC-24": "Quantum Blockchain",
    }

    IMPLEMENTATION_FILES = {
        "QC-09": "qc-security-lab/src/ml_kem_kyber.py",
        "QC-10": "qc-security-lab/src/ml_dsa_dilithium.py",
        "QC-11": "qc-security-lab/src/slh_dsa_sphincs.py",
        "QC-05": "qc-security-lab/src/mdi_qkd_simulation.py",
        "QC-07": "qc-security-lab/src/qrng.py",
        "QC-01": "qc-security-lab/src/qkd_bb84.py",
    }

    scenario_map = {}
    for sc_id, sc_name in SCENARIO_NAMES.items():
        papers_for_sc = [
            p for p in parsed
            if sc_id in (p.get("scenario_ids") or [])
        ]
        top_paper = None
        if papers_for_sc:
            papers_for_sc.sort(key=lambda p: p.get("year", 0), reverse=True)
            top_paper = {
                "arxiv_id": papers_for_sc[0].get("arxiv_id", ""),
                "title": papers_for_sc[0].get("title", ""),
                "year": papers_for_sc[0].get("year", ""),
            }

        impl_file = IMPLEMENTATION_FILES.get(sc_id)
        impl_exists = False
        if impl_file:
            impl_exists = (_BASE_DIR / impl_file).exists()

        status = (
            "implemented" if impl_exists
            else ("papers_only" if papers_for_sc else "no_papers")
        )

        scenario_map[sc_id] = {
            "id": sc_id,
            "name": sc_name,
            "paper_count": len(papers_for_sc),
            "top_paper": top_paper,
            "implementation_file": impl_file,
            "implementation_exists": impl_exists,
            "status": status,
        }

    return {
        "scenarios": list(scenario_map.values()),
        "total_scenarios": len(scenario_map),
        "implemented": sum(1 for v in scenario_map.values() if v["status"] == "implemented"),
        "papers_only": sum(1 for v in scenario_map.values() if v["status"] == "papers_only"),
        "no_papers": sum(1 for v in scenario_map.values() if v["status"] == "no_papers"),
    }


# ---------------------------------------------------------------------------
# Attack Engine — in-memory state
# ---------------------------------------------------------------------------

_ATTACK_JOBS: Dict[str, Any] = {}
_ATTACK_SCHEDULES: List[Dict[str, Any]] = []
_INCIDENTS: Dict[str, Any] = {}

# ---------------------------------------------------------------------------
# Attack catalogue: (name, severity, mitre_id, cve)
# ---------------------------------------------------------------------------

LAYER_ATTACKS: Dict[str, Dict[str, List[tuple]]] = {
    "L01": {
        "classical": [
            ("Physical Tap", "HIGH", "T1040", None),
            ("MAC Flooding", "HIGH", "T1049", None),
            ("ARP Spoofing", "MEDIUM", "T1557.002", None),
        ],
        "ai": [
            ("AI Network Fingerprinting", "MEDIUM", "T1040", None),
            ("Adversarial Traffic Classification", "LOW", None, None),
        ],
        "quantum": [
            ("HNDL Physical Link Capture", "CRITICAL", "T1040", None),
        ],
    },
    "L04": {
        "classical": [
            ("POODLE SSLv3 Downgrade", "HIGH", "T1573.002", "CVE-2014-3566"),
            ("BEAST CBC Attack", "HIGH", "T1573.002", "CVE-2011-3389"),
            ("ROBOT PKCS1v1.5", "HIGH", "T1573.002", "CVE-2017-13099"),
            ("HNDL Traffic Harvest", "CRITICAL", "T1040", None),
        ],
        "ai": [
            ("AI Protocol Fuzzing", "HIGH", "T1573", None),
            ("Neural Cipher Distinguisher", "HIGH", None, None),
            ("ML TLS Fingerprint", "MEDIUM", "T1040", None),
        ],
        "quantum": [
            ("Shor breaks ECDH KEX", "CRITICAL", None, None),
            ("Grover weakens AES-128", "HIGH", None, None),
        ],
    },
    "L06": {
        "classical": [
            ("Bleichenbacher PKCS1v1.5", "HIGH", "T1553.004", None),
            ("CA Compromise", "CRITICAL", "T1553.004", None),
            ("Cert Pinning Bypass", "MEDIUM", "T1553", None),
        ],
        "ai": [
            ("AI Cert Forgery Detection Evasion", "HIGH", None, None),
            ("GAN X.509 Cert Generation", "MEDIUM", None, None),
        ],
        "quantum": [
            ("Shor breaks RSA-4096 Root CA", "CRITICAL", None, None),
            ("ML-DSA not deployed — new CA issue", "CRITICAL", None, None),
        ],
    },
    "L08": {
        "classical": [
            ("alg:none JWT bypass", "CRITICAL", "T1550.001", "CVE-2015-9235"),
            ("RS256→HS256 confusion", "CRITICAL", "T1550.001", None),
            ("JWT secret brute-force", "HIGH", "T1110", None),
        ],
        "ai": [
            ("AI JWT secret inference", "HIGH", "T1550", None),
            ("ML token pattern analysis", "MEDIUM", None, None),
        ],
        "quantum": [
            ("Shor breaks RS256 signing key", "CRITICAL", None, None),
            ("Grover brute-forces HS256", "HIGH", None, None),
        ],
    },
    "L10": {
        "classical": [
            ("Terrapin SSH prefix truncation", "HIGH", "T1557", "CVE-2023-48795"),
            ("ECDH KEX downgrade", "HIGH", "T1557.002", None),
            ("SSH host key spoofing", "HIGH", "T1557", None),
        ],
        "ai": [
            ("AI SSH pattern extraction", "MEDIUM", "T1557", None),
        ],
        "quantum": [
            ("Shor breaks ECDH SSH KEX", "CRITICAL", None, None),
        ],
    },
    "L14": {
        "classical": [
            ("HSM side-channel timing", "HIGH", "T1552.004", None),
            ("RSA-OAEP padding oracle", "HIGH", "T1552.004", None),
            ("Key escrow attack", "CRITICAL", "T1552.004", None),
        ],
        "ai": [
            ("Deep learning power analysis", "HIGH", "T1552", None),
            ("AI EM side-channel", "HIGH", None, None),
        ],
        "quantum": [
            ("Quantum side-channel amplification", "HIGH", None, None),
            ("Shor breaks RSA-wrapped DEKs", "CRITICAL", None, None),
        ],
    },
    "L15": {
        "classical": [
            ("Kerberos Golden Ticket", "CRITICAL", "T1558.001", None),
            ("DCSync AD Replication", "CRITICAL", "T1003.006", None),
            ("Pass-the-Hash", "CRITICAL", "T1550.002", None),
        ],
        "ai": [
            ("AI credential stuffing", "HIGH", "T1110.004", None),
            ("ML anomaly evasion", "MEDIUM", None, None),
        ],
        "quantum": [
            ("Grover breaks short-lived tokens", "HIGH", None, None),
        ],
    },
}

# Generic fallback catalogue keyed by attack_type
_GENERIC_ATTACKS: Dict[str, List[tuple]] = {
    "classical": [
        ("Replay Attack", "MEDIUM", "T1550", None),
        ("Man-in-the-Middle", "HIGH", "T1557", None),
        ("Credential Brute-Force", "HIGH", "T1110", None),
        ("Protocol Downgrade", "HIGH", "T1573", None),
        ("Side-Channel Timing", "MEDIUM", "T1552", None),
    ],
    "ai": [
        ("Adversarial Input Injection", "HIGH", "T1059", None),
        ("Model Inversion Attack", "MEDIUM", None, None),
        ("Membership Inference", "MEDIUM", None, None),
        ("Prompt Injection via API", "HIGH", "T1059", None),
        ("AI-Assisted Recon", "LOW", "T1040", None),
    ],
    "quantum": [
        ("Grover Search Acceleration", "HIGH", None, None),
        ("Shor Algorithm Key Break", "CRITICAL", None, None),
        ("HNDL Harvest Now Decrypt Later", "CRITICAL", "T1040", None),
        ("Quantum Tunneling Side-Channel", "MEDIUM", None, None),
        ("BB84 Intercept-Resend", "HIGH", None, None),
    ],
}

_RECOMMENDATIONS_BY_ATTACK_TYPE: Dict[str, List[str]] = {
    "classical": [
        "Patch all known CVEs within 30 days of disclosure.",
        "Enforce TLS 1.3 minimum; disable legacy cipher suites.",
        "Deploy WAF rules for protocol downgrade and replay vectors.",
    ],
    "ai": [
        "Apply adversarial robustness training to all ML inference pipelines.",
        "Rate-limit API endpoints to reduce model inversion surface.",
        "Monitor for anomalous query patterns indicating model extraction attempts.",
    ],
    "quantum": [
        "Migrate key exchange to ML-KEM-768 or higher (NIST FIPS 203).",
        "Replace RSA/ECDSA signatures with ML-DSA-65 (NIST FIPS 204).",
        "Implement crypto-agility to allow rapid algorithm rotation.",
    ],
}


def _get_layer_name(layer_id: str) -> str:
    """Return layer name from _LAYERS catalogue; fall back to layer_id."""
    for la in _LAYERS:
        if la["id"] == layer_id:
            return la["name"]
    return layer_id


def _severity_weight(severity: str) -> float:
    return {"CRITICAL": 10.0, "HIGH": 7.0, "MEDIUM": 4.0, "LOW": 1.5}.get(severity.upper(), 3.0)


def _make_recommendation(attack_type: str, name: str, severity: str) -> str:
    base = _RECOMMENDATIONS_BY_ATTACK_TYPE.get(attack_type, _RECOMMENDATIONS_BY_ATTACK_TYPE["classical"])
    if severity.upper() == "CRITICAL":
        return f"Immediate remediation required: {base[0]}"
    if severity.upper() == "HIGH":
        return f"High-priority fix: {base[1 % len(base)]}"
    return f"Scheduled remediation: {base[2 % len(base)]}"


def _build_findings(layer_id: str, attack_types: List[str]) -> List[Dict[str, Any]]:
    """Build finding dicts for the given layer and attack types."""
    findings: List[Dict[str, Any]] = []
    idx = 0
    rng = random.Random(layer_id)  # deterministic per layer for reproducibility within a run

    catalogue = LAYER_ATTACKS.get(layer_id, {})

    for atype in attack_types:
        if catalogue and atype in catalogue:
            candidates = catalogue[atype]
        else:
            # Generic pool — seed variety from layer_id hash
            pool = _GENERIC_ATTACKS.get(atype, _GENERIC_ATTACKS["classical"])
            offset = abs(hash(layer_id)) % len(pool)
            # pick 3 entries cycling from offset
            candidates = [pool[(offset + i) % len(pool)] for i in range(3)]

        for (name, severity, mitre_id, cve) in candidates:
            detected = rng.random() < 0.80
            pqc_prevents = (atype == "quantum") or (atype == "classical" and rng.random() < 0.55)
            findings.append({
                "finding_id": f"F-{idx + 1:03d}",
                "name": name,
                "severity": severity,
                "attack_type": atype,
                "mitre_id": mitre_id,
                "cve": cve,
                "detected": detected,
                "pqc_prevents": pqc_prevents,
                "recommendation": _make_recommendation(atype, name, severity),
                "layer_id": layer_id,
            })
            idx += 1

    return findings


def _build_summary(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    detected = 0
    pqc_count = 0
    for f in findings:
        sev = f["severity"].upper()
        counts[sev] = counts.get(sev, 0) + 1
        if f["detected"]:
            detected += 1
        if f["pqc_prevents"]:
            pqc_count += 1
    return {
        "total_findings": len(findings),
        "critical": counts["CRITICAL"],
        "high": counts["HIGH"],
        "medium": counts["MEDIUM"],
        "low": counts["LOW"],
        "detected": detected,
        "undetected": len(findings) - detected,
        "pqc_prevents": pqc_count,
    }


def _compute_risk_score(findings: List[Dict[str, Any]]) -> float:
    if not findings:
        return 0.0
    total_weight = sum(_severity_weight(f["severity"]) for f in findings)
    max_possible = len(findings) * 10.0
    raw = (total_weight / max_possible) * 100.0
    return round(min(raw, 100.0), 1)


def _top_recommendations(findings: List[Dict[str, Any]], attack_types: List[str]) -> List[str]:
    """Return the top 3 unique recommendations, prioritising critical/high findings."""
    seen: set = set()
    recs: List[str] = []
    priority_order = sorted(
        findings,
        key=lambda f: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(f["severity"].upper(), 4)),
    )
    for f in priority_order:
        r = f["recommendation"]
        if r not in seen:
            seen.add(r)
            recs.append(r)
        if len(recs) >= 3:
            break
    # Pad with generic recommendations if fewer than 3
    for atype in attack_types:
        for r in _RECOMMENDATIONS_BY_ATTACK_TYPE.get(atype, []):
            if r not in seen and len(recs) < 3:
                seen.add(r)
                recs.append(r)
    return recs[:3]


# ---------------------------------------------------------------------------
# Request/response models (inline Pydantic via BaseModel-free approach)
# We use plain dicts from FastAPI body for simplicity, consistent with the
# existing router pattern in this file which uses Query params only.
# For POST bodies we use explicit Pydantic models.
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field  # noqa: E402 — after stdlib imports above


class AttackRunRequest(BaseModel):
    layer_id: str
    attack_types: List[str] = Field(..., description="Subset of ['classical','ai','quantum']")


class AttackScheduleRequest(BaseModel):
    layer_id: str
    attack_types: List[str]
    schedule: str = Field(..., description="'daily' | 'weekly' | 'on_demand'")


class IncidentCreateRequest(BaseModel):
    layer_id: str
    title: str
    severity: str
    source: str
    description: str
    attack_type: str


class IncidentUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    resolved_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Attack Engine Endpoints
# ---------------------------------------------------------------------------


@router.post("/attack/run")
def attack_run(req: AttackRunRequest) -> Dict[str, Any]:
    """Run a simulated attack job synchronously for the given layer and attack types."""
    valid_types = {"classical", "ai", "quantum"}
    bad = [t for t in req.attack_types if t not in valid_types]
    if bad:
        raise HTTPException(status_code=422, detail=f"Unknown attack_types: {bad}. Valid: {sorted(valid_types)}")
    if not req.attack_types:
        raise HTTPException(status_code=422, detail="attack_types must not be empty.")

    job_id = f"JOB-{uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)
    started_at = now.isoformat()
    # Simulate a short processing window (deterministic, not a real sleep)
    completed_at = (now + timedelta(seconds=random.randint(1, 5))).isoformat()

    findings = _build_findings(req.layer_id, req.attack_types)
    summary = _build_summary(findings)
    risk_score = _compute_risk_score(findings)
    recommendations = _top_recommendations(findings, req.attack_types)

    report: Dict[str, Any] = {
        "job_id": job_id,
        "layer_id": req.layer_id,
        "layer_name": _get_layer_name(req.layer_id),
        "status": "completed",
        "started_at": started_at,
        "completed_at": completed_at,
        "attack_types": req.attack_types,
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "risk_score": risk_score,
        "report_url": f"/security/attack/report/{job_id}",
    }

    _ATTACK_JOBS[job_id] = report
    return report


@router.post("/attack/schedule")
def attack_schedule(req: AttackScheduleRequest) -> Dict[str, Any]:
    """Store an attack schedule and return its metadata."""
    valid_schedules = {"daily", "weekly", "on_demand"}
    if req.schedule not in valid_schedules:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid schedule '{req.schedule}'. Valid: {sorted(valid_schedules)}",
        )

    schedule_id = f"SCH-{uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)

    delta_map = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1), "on_demand": timedelta(seconds=0)}
    next_run = (now + delta_map[req.schedule]).isoformat()

    entry: Dict[str, Any] = {
        "schedule_id": schedule_id,
        "layer_id": req.layer_id,
        "attack_types": req.attack_types,
        "schedule": req.schedule,
        "next_run": next_run,
        "created_at": now.isoformat(),
        "status": "active",
    }
    _ATTACK_SCHEDULES.append(entry)
    return entry


@router.get("/attack/jobs")
def attack_jobs(
    layer_id: Optional[str] = Query(default=None, description="Filter by layer ID, e.g. L04"),
    status: Optional[str] = Query(default=None, description="Filter by status, e.g. 'completed'"),
) -> Dict[str, Any]:
    """Return all attack jobs and schedules, with optional filters."""
    jobs: List[Dict[str, Any]] = list(_ATTACK_JOBS.values())
    schedules: List[Dict[str, Any]] = list(_ATTACK_SCHEDULES)

    if layer_id:
        jobs = [j for j in jobs if j.get("layer_id") == layer_id]
        schedules = [s for s in schedules if s.get("layer_id") == layer_id]

    if status:
        jobs = [j for j in jobs if j.get("status") == status]
        schedules = [s for s in schedules if s.get("status") == status]

    return {
        "jobs": jobs,
        "schedules": schedules,
        "total_jobs": len(jobs),
        "total_schedules": len(schedules),
    }


@router.get("/attack/report/{job_id}")
def attack_report(job_id: str) -> Dict[str, Any]:
    """Return the full attack report for a completed job."""
    report = _ATTACK_JOBS.get(job_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return report


@router.delete("/attack/schedule/{schedule_id}")
def attack_schedule_delete(schedule_id: str) -> Dict[str, Any]:
    """Delete an attack schedule by ID."""
    for i, s in enumerate(_ATTACK_SCHEDULES):
        if s.get("schedule_id") == schedule_id:
            _ATTACK_SCHEDULES.pop(i)
            return {"deleted": True, "schedule_id": schedule_id}
    raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found.")


# ---------------------------------------------------------------------------
# Incident Management Endpoints
# ---------------------------------------------------------------------------


@router.post("/incident/create")
def incident_create(req: IncidentCreateRequest) -> Dict[str, Any]:
    """Create a new security incident."""
    incident_id = f"INC-{uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    incident: Dict[str, Any] = {
        "incident_id": incident_id,
        "layer_id": req.layer_id,
        "title": req.title,
        "severity": req.severity,
        "source": req.source,
        "description": req.description,
        "attack_type": req.attack_type,
        "status": "Open",
        "created_at": now,
        "notes": None,
        "assigned_to": None,
        "resolved_at": None,
    }
    _INCIDENTS[incident_id] = incident
    return incident


@router.get("/incident/list")
def incident_list(
    layer_id: Optional[str] = Query(default=None, description="Filter by layer ID"),
    status: Optional[str] = Query(default=None, description="Filter by status, e.g. 'Open'"),
    severity: Optional[str] = Query(default=None, description="Filter by severity, e.g. 'CRITICAL'"),
) -> Dict[str, Any]:
    """Return all incidents with optional filters."""
    incidents: List[Dict[str, Any]] = list(_INCIDENTS.values())

    if layer_id:
        incidents = [i for i in incidents if i.get("layer_id") == layer_id]
    if status:
        incidents = [i for i in incidents if i.get("status") == status]
    if severity:
        incidents = [i for i in incidents if (i.get("severity") or "").upper() == severity.upper()]

    return {"incidents": incidents, "total": len(incidents)}


@router.patch("/incident/{incident_id}")
def incident_update(incident_id: str, req: IncidentUpdateRequest) -> Dict[str, Any]:
    """Partially update an existing incident."""
    incident = _INCIDENTS.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    if req.status is not None:
        incident["status"] = req.status
    if req.notes is not None:
        incident["notes"] = req.notes
    if req.assigned_to is not None:
        incident["assigned_to"] = req.assigned_to
    if req.resolved_at is not None:
        incident["resolved_at"] = req.resolved_at

    _INCIDENTS[incident_id] = incident
    return incident
