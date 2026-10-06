"""
SBOM Generator — Classical Security Lab
Produces CycloneDX 1.4 SBOM, CycloneDX 1.6 CBOM (crypto extension),
a quantum-risk report, and an EDR agent deployment manifest.

All data is derived from oss_registry.OSSRegistry — no hard-coded
duplicates.  Only Python stdlib is used.

Classes
-------
SBOMGenerator
    generate_sbom()         → CycloneDX 1.4 dict
    generate_cbom()         → CycloneDX 1.6 cryptographic BOM dict
    quantum_risk_report()   → per-component quantum risk + migration plan
    generate_edr_manifest() → per-layer EDR agent deployment manifest

Functions
---------
main()  — prints SBOM stats, CBOM summary, and EDR manifest overview
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

# Allow running the file directly even if the module is not installed
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from oss_registry import OSSRegistry


# ---------------------------------------------------------------------------
# Helper: classify quantum risk
# ---------------------------------------------------------------------------

def _classify_risk(sw: dict[str, Any]) -> dict[str, Any]:
    """Return quantum-risk metadata for a single software entry."""
    algo = sw.get("crypto_algorithm", "").lower()
    vulnerable = sw.get("quantum_vulnerable", False)

    # Determine which quantum algorithm breaks this component
    if not vulnerable:
        breaking_algo = "None"
        risk_level = "LOW"
        migration_priority = "P3"
    elif any(k in algo for k in ("rsa", "dh-", "diffie")):
        breaking_algo = "Shor's algorithm"
        risk_level = "CRITICAL"
        migration_priority = "P0"
    elif any(k in algo for k in ("ecdsa", "ecdh", "ecdhe", "ecc", "ec ", "curve25519", "secp256")):
        breaking_algo = "Shor's algorithm"
        risk_level = "CRITICAL"
        migration_priority = "P0"
    elif any(k in algo for k in ("aes-128", "hmac", "sha-256", "sha256")):
        # Symmetric / hash — Grover halves effective key length
        breaking_algo = "Grover's algorithm (key-length reduction)"
        risk_level = "MEDIUM"
        migration_priority = "P2"
    elif any(k in algo for k in ("aes-256", "aes-gcm")):
        breaking_algo = "Grover's algorithm (manageable — AES-256 → 128-bit)"
        risk_level = "LOW"
        migration_priority = "P3"
    else:
        breaking_algo = "Shor's algorithm"  # default for unknown asymmetric
        risk_level = "HIGH"
        migration_priority = "P1"

    # Suggested PQC migration target
    pqc_migration: dict[str, str] = {
        "CRITICAL": "NIST FIPS 203 ML-KEM (Kyber) / FIPS 204 ML-DSA (Dilithium)",
        "HIGH":     "NIST FIPS 204 ML-DSA or SLH-DSA depending on use case",
        "MEDIUM":   "Upgrade to AES-256; add SHA-3/SHA-512 where hashes are exposed",
        "LOW":      "No migration required; monitor NIST post-quantum standards",
    }

    return {
        "quantum_risk": risk_level,
        "breaking_algorithm": breaking_algo,
        "migration_priority": migration_priority,
        "recommended_pqc": pqc_migration[risk_level],
    }


# ---------------------------------------------------------------------------
# EDR detection rules per layer type
# ---------------------------------------------------------------------------

_EDR_RULES: dict[str, dict[str, Any]] = {
    "L01": {
        "agent": "Wazuh + Prometheus node_exporter",
        "monitors": ["TPM PCR register changes", "PRNG entropy drain", "OpenSSL version drift"],
        "alert_thresholds": {"cpu_crypto_load_pct": 80, "tpm_event_rate_per_min": 100},
        "detection_rules": [
            "RULE-HW-001: TPM PCR[0] change → firmware tamper alert",
            "RULE-HW-002: OpenSSL version < 3.0 detected → upgrade alert",
            "RULE-HW-003: Entropy pool below 256 bytes → PRNG starvation alert",
        ],
    },
    "L02": {
        "agent": "tcpdump + Wireshark (tshark headless)",
        "monitors": ["MACsec session drops", "WPA3 downgrade attempts", "EAP-TLS failures"],
        "alert_thresholds": {"macsec_drop_rate_per_sec": 10, "eap_fail_per_min": 5},
        "detection_rules": [
            "RULE-DL-001: WPA2 association on WPA3 AP → downgrade attack",
            "RULE-DL-002: EAP-TLS cert rejected 5× in 1 min → brute-force attempt",
        ],
    },
    "L03": {
        "agent": "Suricata IDS + Prometheus",
        "monitors": ["IKE handshake anomalies", "DH group negotiation", "IPsec SA expiry"],
        "alert_thresholds": {"ike_fail_per_min": 3, "dh_group_below": 14},
        "detection_rules": [
            "RULE-NET-001: IKEv1 negotiation detected → deprecation alert",
            "RULE-NET-002: DH group < 14 (2048-bit) → weak-key alert",
            "RULE-NET-003: Suricata ET/SCAN rule hit on VPN subnet → lateral movement",
        ],
    },
    "L04": {
        "agent": "testssl.sh (nightly) + sslyze + Prometheus TLS exporter",
        "monitors": ["TLS version", "cipher suite", "cert expiry", "HNDL detection"],
        "alert_thresholds": {
            "tls_version_min": "TLSv1.3",
            "cert_expiry_warn_days": 30,
            "hndl_record_size_bytes": 32768,
        },
        "detection_rules": [
            "RULE-TLS-001: TLS 1.0/1.1 handshake → immediate block + alert",
            "RULE-TLS-002: TLS 1.2 handshake on public endpoint → HIGH alert (HNDL risk)",
            "RULE-TLS-003: Cert expires < 30 days → cert-renewal alert",
            "RULE-TLS-004: Cipher suite without PFS → WARNING",
            "RULE-TLS-005: RSA key-exchange (not ECDHE) detected → CRITICAL",
        ],
    },
    "L05": {
        "agent": "Redis Insight + custom session analytics",
        "monitors": ["Session TTL drift", "HMAC validation failures", "Redis key-space events"],
        "alert_thresholds": {"session_hmac_fail_per_min": 20, "redis_memory_used_pct": 85},
        "detection_rules": [
            "RULE-SES-001: Session replay (same token, different IP) → invalidate + alert",
            "RULE-SES-002: HMAC verify fail burst → token-forgery attempt",
        ],
    },
    "L06": {
        "agent": "cert-manager metrics + certbot renewal monitor",
        "monitors": ["Certificate chain RSA key size", "CRL/OCSP freshness", "CA cert expiry"],
        "alert_thresholds": {"rsa_key_min_bits": 2048, "cert_expiry_warn_days": 30, "ocsp_max_age_hours": 24},
        "detection_rules": [
            "RULE-PKI-001: RSA key < 2048 in cert chain → CRITICAL revoke + reissue",
            "RULE-PKI-002: RSA-1024 root CA detected → CRITICAL escalation",
            "RULE-PKI-003: OCSP response age > 24 h → CRL staleness alert",
            "RULE-PKI-004: CA cert expires < 90 days → emergency renewal ticket",
        ],
    },
    "L07": {
        "agent": "Prometheus nginx_exporter + OWASP ZAP (weekly scan)",
        "monitors": ["HTTP security headers", "TLS config", "WAF rule hits", "injection attempts"],
        "alert_thresholds": {"waf_block_per_min": 50, "missing_hsts_header": True},
        "detection_rules": [
            "RULE-APP-001: Missing HSTS header → configuration drift alert",
            "RULE-APP-002: ZAP high-severity finding → P0 remediation ticket",
            "RULE-APP-003: nginx TLS error spike → possible downgrade/DoS",
        ],
    },
    "L08": {
        "agent": "Keycloak metrics exporter + JWT validation log aggregator",
        "monitors": ["JWT algorithm", "token expiry", "algorithm confusion attempts"],
        "alert_thresholds": {"alg_none_attempts_per_hour": 1, "token_exp_skew_seconds": 30},
        "detection_rules": [
            "RULE-JWT-001: alg=none in JWT header → CRITICAL block + alert",
            "RULE-JWT-002: HS256 presented where RS256 expected → algo-confusion attack",
            "RULE-JWT-003: Expired token reuse → replay-attack alert",
            "RULE-JWT-004: RS256 key < 2048 bits → key rotation alert",
        ],
    },
    "L09": {
        "agent": "Prometheus DNS metrics + dnsviz (weekly)",
        "monitors": ["DNSSEC validation failures", "RRSIG expiry", "zone transfer anomalies"],
        "alert_thresholds": {"dnssec_fail_per_min": 5, "rrsig_expiry_warn_days": 7},
        "detection_rules": [
            "RULE-DNS-001: DNSSEC bogus response → resolver block + alert",
            "RULE-DNS-002: Unauthorized zone transfer attempt → CRITICAL",
            "RULE-DNS-003: RRSIG expires < 7 days → re-sign alert",
        ],
    },
    "L10": {
        "agent": "fail2ban + ssh-audit + Wazuh",
        "monitors": ["SSH brute force", "algorithm negotiation", "PQ KEX availability"],
        "alert_thresholds": {"auth_fail_per_min": 5, "non_pq_kex_pct": 100},
        "detection_rules": [
            "RULE-SSH-001: 5 auth failures in 60 s → fail2ban ban (30 min)",
            "RULE-SSH-002: ssh-keysign RSA-1024 → reject + alert",
            "RULE-SSH-003: PQ KEX not negotiated → informational (enforce by Q3 2025)",
            "RULE-SSH-004: Root login permitted → HIGH alert",
        ],
    },
    "L11": {
        "agent": "Postfix log monitor + mail security header checks",
        "monitors": ["DKIM signature failures", "SPF hard-fail", "DMARC quarantine rate"],
        "alert_thresholds": {"dkim_fail_pct": 5, "dmarc_quarantine_pct": 10},
        "detection_rules": [
            "RULE-MAIL-001: DKIM verify fail > 5% → key rotation check",
            "RULE-MAIL-002: SPF hard-fail for own domain → spoofing attempt",
            "RULE-MAIL-003: Expired PGP key used to sign → key refresh alert",
        ],
    },
    "L12": {
        "agent": "Sigstore transparency log verifier (rekor-cli)",
        "monitors": ["Unsigned commits in main branch", "cosign signature validity", "in-toto layout"],
        "alert_thresholds": {"unsigned_commit_count": 0},
        "detection_rules": [
            "RULE-CS-001: Unsigned commit merged to main → CRITICAL gate failure",
            "RULE-CS-002: cosign verify fails for production image → deploy block",
            "RULE-CS-003: in-toto step link missing → supply-chain integrity failure",
        ],
    },
    "L13": {
        "agent": "Prometheus VPN metrics + custom keepalive monitor",
        "monitors": ["VPN tunnel uptime", "cipher negotiation", "split-tunnel policy"],
        "alert_thresholds": {"tunnel_down_seconds": 30, "dh_group_below": 14},
        "detection_rules": [
            "RULE-VPN-001: OpenVPN cipher BF-CBC detected → block + upgrade alert",
            "RULE-VPN-002: WireGuard peer offline > 30 s → reconnect alert",
            "RULE-VPN-003: DH group < 14 negotiated → weak-PFS alert",
        ],
    },
    "L14": {
        "agent": "Vault audit log exporter + key rotation metrics",
        "monitors": ["Key age", "PKCS11 slot access", "Vault seal status"],
        "alert_thresholds": {"key_age_days_max": 90, "vault_seal_status": "unsealed"},
        "detection_rules": [
            "RULE-KM-001: RSA key age > 90 days → auto-rotation trigger",
            "RULE-KM-002: Vault sealed unexpectedly → CRITICAL on-call page",
            "RULE-KM-003: PKCS11 slot accessed outside maintenance window → alert",
        ],
    },
    "L15": {
        "agent": "LDAP monitor + Keycloak events exporter",
        "monitors": ["Admin privilege grants", "LDAP bind failures", "OIDC token issuance rate"],
        "alert_thresholds": {"ldap_bind_fail_per_min": 10, "priv_grant_per_hour": 5},
        "detection_rules": [
            "RULE-IAM-001: Admin role grant outside change window → CRITICAL alert",
            "RULE-IAM-002: LDAP enumeration (> 500 entries/s) → brute-force alert",
            "RULE-IAM-003: Keycloak OIDC token issued with RS256 < 2048-bit → alert",
        ],
    },
    "L16": {
        "agent": "Kong Prometheus plugin + API gateway rate metrics",
        "monitors": ["OAuth2 token misuse", "mTLS handshake failures", "rate-limit breaches"],
        "alert_thresholds": {"rate_limit_breach_per_min": 100, "mtls_fail_per_min": 20},
        "detection_rules": [
            "RULE-API-001: JWT RS256 key-id unknown → reject 401 + alert",
            "RULE-API-002: mTLS client cert expired → block + notify client",
            "RULE-API-003: Rate-limit breach → temporary IP ban + SIEM event",
        ],
    },
    "L17": {
        "agent": "pg_stat_ssl + slow query log monitor",
        "monitors": ["TLS version on DB connections", "TDE status", "column-level encryption"],
        "alert_thresholds": {"db_tls_version_min": "TLSv1.3", "plaintext_connection_count": 0},
        "detection_rules": [
            "RULE-DB-001: Plaintext DB connection detected → block + CRITICAL alert",
            "RULE-DB-002: TDE key not rotated in 365 days → key rotation ticket",
            "RULE-DB-003: pg_stat_ssl shows TLS < 1.3 → configuration drift",
        ],
    },
    "L18": {
        "agent": "Blockchain explorer + node health metrics",
        "monitors": ["ECDSA public key exposure", "wallet balance thresholds", "unconfirmed tx anomalies"],
        "alert_thresholds": {"wallet_balance_usd_threshold": 10000, "reused_address_count": 0},
        "detection_rules": [
            "RULE-BC-001: P2PK output detected (exposed public key) → quantum-risk flag",
            "RULE-BC-002: Address reuse → CRITICAL (public key exposed, Shor risk)",
            "RULE-BC-003: Wallet with > $10K USD in P2PK → CRITICAL quantum migration alert",
            "RULE-BC-004: ECDSA signing with deterministic k confirmed → monitor for Shor timeline",
        ],
    },
    "L19": {
        "agent": "Istio telemetry + SPIRE health exporter",
        "monitors": ["mTLS policy enforcement", "SVID expiry", "container image signatures"],
        "alert_thresholds": {"svid_expiry_warn_minutes": 60, "plaintext_mesh_traffic_pct": 0},
        "detection_rules": [
            "RULE-MESH-001: Plaintext traffic in service mesh → mTLS policy violation",
            "RULE-MESH-002: SVID expires < 60 min → SPIRE rotation trigger",
            "RULE-MESH-003: Unsigned container image admitted → supply-chain alert",
        ],
    },
    "L20": {
        "agent": "MQTT broker metrics + IoT device health dashboard",
        "monitors": ["DTLS handshake failures", "firmware version drift", "MQTT topic ACL violations"],
        "alert_thresholds": {"dtls_fail_per_device_per_hour": 3, "firmware_version_lag_days": 30},
        "detection_rules": [
            "RULE-IOT-001: Device connecting over unencrypted MQTT → block + alert",
            "RULE-IOT-002: Firmware version lag > 30 days → patch ticket",
            "RULE-IOT-003: DTLS 1.0 negotiated → upgrade enforced",
        ],
    },
    "L21": {
        "agent": "Certificate pinning failure logger + TLS version dashboard",
        "monitors": ["Pin validation failures", "TLS downgrade on mobile", "cert chain depth"],
        "alert_thresholds": {"pin_fail_per_app_per_day": 5},
        "detection_rules": [
            "RULE-MOB-001: Cert-pin failure → possible MITM on mobile network",
            "RULE-MOB-002: TLS < 1.2 on mobile client → block + force upgrade",
        ],
    },
    "L22": {
        "agent": "TPM attestation status daemon + firmware version tracker",
        "monitors": ["Secure boot verification", "PCR log integrity", "firmware update signatures"],
        "alert_thresholds": {"pcr_change_outside_maintenance": True, "unsigned_firmware_update": True},
        "detection_rules": [
            "RULE-FW-001: Secure boot disabled → CRITICAL halt boot sequence",
            "RULE-FW-002: Unsigned firmware update attempted → block + alert",
            "RULE-FW-003: Keylime attestation failure → quarantine node",
        ],
    },
    "L23": {
        "agent": "Trivy CI scan + secrets-detection pre-commit hooks",
        "monitors": ["Container CVEs", "hardcoded secrets", "SBOM freshness"],
        "alert_thresholds": {"critical_cve_count": 0, "high_cve_count": 5},
        "detection_rules": [
            "RULE-CICD-001: Critical CVE in build image → pipeline block",
            "RULE-CICD-002: Secret in git commit → immediate revoke + rotate",
            "RULE-CICD-003: SBOM not regenerated after dependency update → drift alert",
        ],
    },
    "L24": {
        "agent": "Wazuh SIEM (self-monitoring via built-in health checks)",
        "monitors": ["Agent connectivity", "log ingestion lag", "rule match rate"],
        "alert_thresholds": {"log_lag_seconds": 60, "agent_offline_count": 0},
        "detection_rules": [
            "RULE-SIEM-001: Wazuh agent offline > 5 min → CRITICAL escalation",
            "RULE-SIEM-002: Log ingestion lag > 60 s → pipeline health check",
            "RULE-SIEM-003: TLS cert on log shipper expired → plaintext-exposure risk",
        ],
    },
    "L25": {
        "agent": "SPIRE health exporter + Pomerium access log",
        "monitors": ["SVID issuance rate", "zero-trust policy violations", "lateral movement"],
        "alert_thresholds": {"zt_policy_deny_per_min": 10, "svid_reuse_count": 0},
        "detection_rules": [
            "RULE-ZT-001: SVID reuse after rotation → possible replay attack",
            "RULE-ZT-002: Zero-trust policy deny spike → lateral movement investigation",
            "RULE-ZT-003: Cilium policy bypass attempt → network-policy alert",
        ],
    },
    "L26": {
        "agent": "Vault metrics exporter + key rotation event stream",
        "monitors": ["Key rotation schedule", "Vault token lease expiry", "seal/unseal events"],
        "alert_thresholds": {"key_rotation_overdue_days": 1, "vault_token_ttl_min": 3600},
        "detection_rules": [
            "RULE-KMS-001: Key rotation overdue → auto-rotation + alert",
            "RULE-KMS-002: Root Vault token used → CRITICAL audit required",
            "RULE-KMS-003: Sealed Secrets RSA key age > 365 days → rotation ticket",
        ],
    },
    "L27": {
        "agent": "OpenSCAP scheduler + Falco runtime monitor",
        "monitors": ["FIPS 140-2 compliance posture", "CIS benchmark drift", "runtime syscall anomalies"],
        "alert_thresholds": {"scap_fail_count": 0, "falco_critical_per_hour": 1},
        "detection_rules": [
            "RULE-COMP-001: SCAP FIPS check failure → compliance incident ticket",
            "RULE-COMP-002: Falco critical rule match (e.g. /etc/passwd write) → incident",
            "RULE-COMP-003: CIS drift detected post-patch → re-harden checklist",
        ],
    },
    "L28": {
        "agent": "Timestamp validation daemon + audit trail completeness checker",
        "monitors": ["RFC 3161 timestamp freshness", "audit log gaps", "hash-chain integrity"],
        "alert_thresholds": {"audit_gap_seconds": 0, "timestamp_age_max_hours": 48},
        "detection_rules": [
            "RULE-AUD-001: Audit log gap detected → evidence-tampering alert",
            "RULE-AUD-002: RFC 3161 timestamp verify fails → non-repudiation breach",
            "RULE-AUD-003: Hash-chain break in immutable log → CRITICAL investigation",
        ],
    },
    "L29": {
        "agent": "Model drift detector + MLflow API anomaly monitor",
        "monitors": ["Model signature validity", "API JWT freshness", "container CVE exposure"],
        "alert_thresholds": {"model_drift_score": 0.15, "jwt_rs256_key_bits_min": 2048},
        "detection_rules": [
            "RULE-AI-001: Model signature (cosign) invalid → block model load",
            "RULE-AI-002: MLflow JWT RS256 key < 2048 bits → key rotation",
            "RULE-AI-003: Model drift score > 0.15 → retrain trigger + audit log",
            "RULE-AI-004: ONNX Runtime serving over non-TLS → CRITICAL block",
        ],
    },
}


# ---------------------------------------------------------------------------
# SBOMGenerator class
# ---------------------------------------------------------------------------

class SBOMGenerator:
    """Generates SBOM, CBOM, quantum risk report, and EDR manifest."""

    def __init__(self) -> None:
        self._registry = OSSRegistry()

    # ------------------------------------------------------------------
    # CycloneDX 1.4 SBOM
    # ------------------------------------------------------------------

    def generate_sbom(self) -> dict[str, Any]:
        """Return a CycloneDX 1.4 SBOM derived from OSSRegistry."""
        return self._registry.generate_sbom()

    # ------------------------------------------------------------------
    # CycloneDX 1.6 CBOM (Cryptographic BOM)
    # ------------------------------------------------------------------

    def generate_cbom(self) -> dict[str, Any]:
        """Return a CycloneDX 1.6 Cryptographic BOM.

        Each component carries the cryptographic extension fields:
        algorithm, key_size (estimated), quantum_safe, standard.
        """
        all_sw = self._registry.get_all_software()
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Crypto extension helper
        def _crypto_ext(sw: dict[str, Any]) -> dict[str, Any]:
            algo_raw = sw.get("crypto_algorithm", "").lower()

            # Key-size heuristic
            if "rsa-4096" in algo_raw or "rsa 4096" in algo_raw:
                key_size = 4096
            elif "rsa-2048" in algo_raw or "rsa 2048" in algo_raw or "rsa" in algo_raw:
                key_size = 2048
            elif "p-256" in algo_raw or "secp256" in algo_raw:
                key_size = 256
            elif "aes-256" in algo_raw:
                key_size = 256
            elif "aes-128" in algo_raw:
                key_size = 128
            elif "curve25519" in algo_raw:
                key_size = 255
            elif "ecdsa" in algo_raw or "ecdh" in algo_raw or "ecdhe" in algo_raw:
                key_size = 256  # P-256 default
            elif "dh-" in algo_raw or "dh+" in algo_raw or "dh " in algo_raw:
                key_size = 2048
            elif "sha-256" in algo_raw or "sha256" in algo_raw:
                key_size = 256
            elif "sha-512" in algo_raw or "sha512" in algo_raw:
                key_size = 512
            elif "hmac" in algo_raw:
                key_size = 256  # typical HMAC-SHA256
            else:
                key_size = 0  # unknown / non-crypto tool

            quantum_safe = not sw["quantum_vulnerable"]

            # Map to NIST/IETF standard
            if "aes" in algo_raw:
                standard = "NIST FIPS 197"
            elif "rsa" in algo_raw:
                standard = "PKCS#1 / NIST SP 800-56B"
            elif "ecdsa" in algo_raw or "ecdh" in algo_raw or "ecdhe" in algo_raw:
                standard = "NIST FIPS 186-4 / RFC 6090"
            elif "curve25519" in algo_raw or "chacha20" in algo_raw:
                standard = "RFC 7748 / RFC 8439"
            elif "tls" in algo_raw:
                standard = "IETF RFC 8446 (TLS 1.3)"
            elif "dnssec" in algo_raw:
                standard = "IETF RFC 4034 / RFC 6840"
            elif "hmac" in algo_raw:
                standard = "FIPS 198-1"
            elif "pgp" in algo_raw:
                standard = "RFC 4880"
            elif "pkcs11" in algo_raw:
                standard = "PKCS#11 v2.40"
            elif "fips 140" in algo_raw:
                standard = "NIST FIPS 140-2/3"
            else:
                standard = "Vendor-defined / no crypto primitives"

            return {
                "algorithm": sw.get("crypto_algorithm", "N/A"),
                "key_size_bits": key_size,
                "quantum_safe": quantum_safe,
                "standard": standard,
            }

        # Build deduplicated component list with crypto extension
        seen: set[tuple[str, str]] = set()
        crypto_components: list[dict[str, Any]] = []
        for sw in all_sw:
            key = (sw["name"], sw["version"])
            if key in seen:
                continue
            seen.add(key)
            cx = _crypto_ext(sw)
            crypto_components.append(
                {
                    "type": "library",
                    "bom-ref": f"cbom-{sw['name'].lower().replace(' ', '-')}-{sw['version']}",
                    "name": sw["name"],
                    "version": sw["version"],
                    "purl": (
                        f"pkg:generic/{sw['name'].lower().replace(' ', '-')}@{sw['version']}"
                    ),
                    "cryptoProperties": {
                        "assetType": "algorithm",
                        "algorithmProperties": {
                            "name": cx["algorithm"],
                            "keySize": cx["key_size_bits"],
                            "primitive": (
                                "asymmetric-encryption"
                                if any(
                                    k in cx["algorithm"].lower()
                                    for k in ("rsa", "ecdsa", "ecdh", "dh")
                                )
                                else (
                                    "hash"
                                    if any(
                                        k in cx["algorithm"].lower()
                                        for k in ("sha", "hmac")
                                    )
                                    else "symmetric-encryption"
                                )
                            ),
                        },
                        "quantumSafe": cx["quantum_safe"],
                        "standard": cx["standard"],
                    },
                    "properties": [
                        {"name": "layer_id", "value": sw["layer_id"]},
                        {"name": "layer_name", "value": sw["layer_name"]},
                        {"name": "language", "value": sw["language"]},
                        {"name": "license", "value": sw["license"]},
                    ],
                }
            )

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": now_iso,
                "tools": [
                    {
                        "vendor": "qc-classical-security-lab",
                        "name": "sbom_generator",
                        "version": "1.0.0",
                        "extension": "cryptographic-bom",
                    }
                ],
                "component": {
                    "type": "application",
                    "name": "qc-classical-security-lab",
                    "version": "1.0.0",
                    "description": "CBOM for 29-layer classical security stack",
                },
            },
            "components": crypto_components,
        }

    # ------------------------------------------------------------------
    # Quantum risk report
    # ------------------------------------------------------------------

    def quantum_risk_report(self) -> dict[str, Any]:
        """Return a per-component quantum risk report.

        Each entry includes:
          - name, version, layer_id, layer_name
          - quantum_risk (CRITICAL / HIGH / MEDIUM / LOW)
          - breaking_algorithm (Shor's / Grover's / None)
          - migration_priority (P0-P3)
          - recommended_pqc (NIST PQC standard to migrate to)
        """
        all_sw = self._registry.get_all_software()

        risk_entries: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for sw in all_sw:
            key = (sw["name"], sw["version"])
            if key in seen:
                continue
            seen.add(key)
            risk_meta = _classify_risk(sw)
            risk_entries.append(
                {
                    "name": sw["name"],
                    "version": sw["version"],
                    "layer_id": sw["layer_id"],
                    "layer_name": sw["layer_name"],
                    "crypto_algorithm": sw["crypto_algorithm"],
                    **risk_meta,
                }
            )

        # Sort: CRITICAL first, then HIGH, MEDIUM, LOW
        _priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        risk_entries.sort(key=lambda e: _priority_order.get(e["quantum_risk"], 9))

        # Summary counts
        summary: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for e in risk_entries:
            summary[e["quantum_risk"]] = summary.get(e["quantum_risk"], 0) + 1

        return {
            "report_title": "Quantum Risk Report — Classical Security Lab (29 layers)",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": summary,
            "total_unique_packages": len(risk_entries),
            "components": risk_entries,
        }

    # ------------------------------------------------------------------
    # EDR manifest
    # ------------------------------------------------------------------

    def generate_edr_manifest(self) -> dict[str, Any]:
        """Return an EDR agent deployment manifest for all 29 layers.

        Each entry specifies the EDR agent, monitored items,
        alert thresholds, and detection rules for that layer.
        """
        all_layers = self._registry._layers
        manifest_entries: list[dict[str, Any]] = []

        for layer in all_layers:
            lid = layer["layer_id"]
            rules = _EDR_RULES.get(lid, {})
            manifest_entries.append(
                {
                    "layer_id": lid,
                    "layer_name": layer["layer_name"],
                    "edr_agent": rules.get("agent", "generic-syslog-collector"),
                    "monitors": rules.get("monitors", []),
                    "alert_thresholds": rules.get("alert_thresholds", {}),
                    "detection_rules": rules.get("detection_rules", []),
                    "software_count": len(layer["software"]),
                    "quantum_vulnerable_count": sum(
                        1 for sw in layer["software"] if sw["quantum_vulnerable"]
                    ),
                }
            )

        return {
            "manifest_title": "EDR Agent Deployment Manifest — Classical Security Lab",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_layers": len(manifest_entries),
            "total_detection_rules": sum(
                len(e["detection_rules"]) for e in manifest_entries
            ),
            "layers": manifest_entries,
        }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    generator = SBOMGenerator()

    # ---- SBOM ----
    sbom = generator.generate_sbom()
    print("=" * 70)
    print("CycloneDX 1.4 SBOM")
    print("=" * 70)
    print(f"  Serial number : {sbom['serialNumber']}")
    print(f"  Generated at  : {sbom['metadata']['timestamp']}")
    print(f"  Components    : {len(sbom['components'])}")

    # ---- CBOM ----
    cbom = generator.generate_cbom()
    print("\n" + "=" * 70)
    print("CycloneDX 1.6 CBOM (Cryptographic BOM)")
    print("=" * 70)
    print(f"  Serial number       : {cbom['serialNumber']}")
    print(f"  Crypto components   : {len(cbom['components'])}")

    quantum_unsafe = sum(
        1 for c in cbom["components"]
        if not c["cryptoProperties"]["quantumSafe"]
    )
    quantum_safe = len(cbom["components"]) - quantum_unsafe
    print(f"  Quantum-safe        : {quantum_safe}")
    print(f"  Quantum-vulnerable  : {quantum_unsafe}")

    # Primitive breakdown
    primitives: dict[str, int] = {}
    for c in cbom["components"]:
        prim = c["cryptoProperties"]["algorithmProperties"]["primitive"]
        primitives[prim] = primitives.get(prim, 0) + 1
    print("\n  --- Crypto primitive breakdown ---")
    for prim, count in sorted(primitives.items(), key=lambda x: -x[1]):
        print(f"    {prim:<40} {count:>3}")

    # ---- Quantum Risk Report ----
    qrr = generator.quantum_risk_report()
    print("\n" + "=" * 70)
    print("Quantum Risk Report")
    print("=" * 70)
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        count = qrr["summary"].get(level, 0)
        bar = "#" * count
        print(f"  {level:<10} {count:>3}  {bar}")

    print(f"\n  Top 10 CRITICAL components:")
    critical = [c for c in qrr["components"] if c["quantum_risk"] == "CRITICAL"][:10]
    for c in critical:
        print(
            f"    [{c['layer_id']}] {c['name']:<25} v{c['version']:<8}"
            f" {c['breaking_algorithm']}"
        )

    # ---- EDR Manifest ----
    edr = generator.generate_edr_manifest()
    print("\n" + "=" * 70)
    print("EDR Agent Deployment Manifest")
    print("=" * 70)
    print(f"  Total layers         : {edr['total_layers']}")
    print(f"  Total detection rules: {edr['total_detection_rules']}")
    print()
    print(f"  {'Layer':<8} {'Name':<30} {'Rules':>6} {'Vuln SW':>8}")
    print("  " + "-" * 58)
    for entry in edr["layers"]:
        print(
            f"  {entry['layer_id']:<8} {entry['layer_name']:<30}"
            f" {len(entry['detection_rules']):>6}  {entry['quantum_vulnerable_count']:>7}"
        )
    print()

    # ---- Optional: dump SBOM JSON ----
    out_path = os.path.join(_HERE, "..", "results", "sbom_cyclonedx14.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(sbom, fh, indent=2)
    print(f"  SBOM JSON saved to: {os.path.abspath(out_path)}")

    cbom_path = os.path.join(_HERE, "..", "results", "cbom_cyclonedx16.json")
    with open(cbom_path, "w", encoding="utf-8") as fh:
        json.dump(cbom, fh, indent=2)
    print(f"  CBOM JSON saved to: {os.path.abspath(cbom_path)}")

    qrr_path = os.path.join(_HERE, "..", "results", "quantum_risk_report.json")
    with open(qrr_path, "w", encoding="utf-8") as fh:
        json.dump(qrr, fh, indent=2)
    print(f"  Quantum risk report saved to: {os.path.abspath(qrr_path)}")
    print()


if __name__ == "__main__":
    main()
