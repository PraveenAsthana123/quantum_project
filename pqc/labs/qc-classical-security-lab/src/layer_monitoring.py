"""
Layer Monitoring — Classical Security Lab
Per-layer health metrics, simulated attack scenarios, and a full
monitoring dashboard for all 29 security layers.

Realistic metrics are pre-seeded for five high-interest layers:
  L04 TLS        health=72  (HNDL warning, TLS 1.2 detected, cert expiry)
  L06 PKI        health=65  (RSA-1024 cert in chain, expiring certs)
  L08 JWT        health=80  (RS256 in use, algorithm confusion detected)
  L10 SSH        health=90  (PQ KEX available but not enforced)
  L18 Blockchain health=40  (ECDSA public keys exposed, $2.3M at risk)

All other layers use a deterministic pseudo-random seed so outputs are
reproducible across runs.

Only Python stdlib is used.

Classes
-------
LayerMonitor
    get_metrics(layer_id)                           → layer metrics dict
    simulate_attack_on_layer(layer_id, attack_type) → attack simulation dict
    get_all_layer_health()                          → list of all 29 health summaries

Functions
---------
main()  — prints full monitoring dashboard to stdout
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from oss_registry import OSSRegistry


# ---------------------------------------------------------------------------
# Layer metadata (ordered L01-L29)
# ---------------------------------------------------------------------------

_LAYER_META: dict[str, dict[str, Any]] = {
    "L01": {
        "name": "Physical / Hardware",
        "criticality": "HIGH",
        "primary_threat": "Hardware implant / PRNG compromise",
    },
    "L02": {
        "name": "Data Link / MACsec",
        "criticality": "HIGH",
        "primary_threat": "Layer-2 eavesdropping / WPA downgrade",
    },
    "L03": {
        "name": "Network / IPsec",
        "criticality": "HIGH",
        "primary_threat": "VPN MITM / weak DH groups",
    },
    "L04": {
        "name": "TLS Transport",
        "criticality": "CRITICAL",
        "primary_threat": "HNDL (Harvest Now Decrypt Later) / TLS downgrade",
    },
    "L05": {
        "name": "Session",
        "criticality": "MEDIUM",
        "primary_threat": "Session replay / token theft",
    },
    "L06": {
        "name": "X.509 PKI",
        "criticality": "CRITICAL",
        "primary_threat": "Weak RSA keys / CA compromise",
    },
    "L07": {
        "name": "HTTPS / Application",
        "criticality": "HIGH",
        "primary_threat": "HTTP injection / weak TLS ciphers",
    },
    "L08": {
        "name": "JWT / Auth Tokens",
        "criticality": "HIGH",
        "primary_threat": "Algorithm confusion / forged tokens",
    },
    "L09": {
        "name": "DNS / DNSSEC",
        "criticality": "HIGH",
        "primary_threat": "DNSSEC bypass / cache poisoning",
    },
    "L10": {
        "name": "SSH",
        "criticality": "HIGH",
        "primary_threat": "Brute force / weak KEX algorithms",
    },
    "L11": {
        "name": "Email S/MIME + PGP",
        "criticality": "MEDIUM",
        "primary_threat": "Key forgery / DKIM bypass",
    },
    "L12": {
        "name": "Code Signing",
        "criticality": "CRITICAL",
        "primary_threat": "Supply-chain attack / unsigned artifacts",
    },
    "L13": {
        "name": "VPN",
        "criticality": "HIGH",
        "primary_threat": "DH weak groups / VPN compromise",
    },
    "L14": {
        "name": "HSM / Key Management",
        "criticality": "CRITICAL",
        "primary_threat": "Key extraction / HSM firmware attack",
    },
    "L15": {
        "name": "Identity / IAM",
        "criticality": "CRITICAL",
        "primary_threat": "Privilege escalation / LDAP injection",
    },
    "L16": {
        "name": "API Security",
        "criticality": "HIGH",
        "primary_threat": "JWT forgery / OAuth token leakage",
    },
    "L17": {
        "name": "Database Encryption",
        "criticality": "HIGH",
        "primary_threat": "Plaintext DB access / TDE bypass",
    },
    "L18": {
        "name": "Blockchain",
        "criticality": "CRITICAL",
        "primary_threat": "Shor ECDSA break / public-key exposure",
    },
    "L19": {
        "name": "Container / Service Mesh",
        "criticality": "HIGH",
        "primary_threat": "mTLS bypass / unsigned images",
    },
    "L20": {
        "name": "IoT / Embedded",
        "criticality": "HIGH",
        "primary_threat": "DTLS downgrade / unpatched firmware",
    },
    "L21": {
        "name": "Mobile",
        "criticality": "MEDIUM",
        "primary_threat": "Cert-pinning bypass / TLS MITM",
    },
    "L22": {
        "name": "Firmware / Secure Boot",
        "criticality": "CRITICAL",
        "primary_threat": "Secure-boot bypass / firmware implant",
    },
    "L23": {
        "name": "DevSecOps / CI-CD",
        "criticality": "HIGH",
        "primary_threat": "Supply-chain injection / secret leakage",
    },
    "L24": {
        "name": "SIEM / Logging",
        "criticality": "HIGH",
        "primary_threat": "Log tampering / agent blindspot",
    },
    "L25": {
        "name": "Zero Trust / SPIFFE",
        "criticality": "HIGH",
        "primary_threat": "SVID forgery / policy bypass",
    },
    "L26": {
        "name": "Key Management / KMS",
        "criticality": "CRITICAL",
        "primary_threat": "Key wrap oracle / rotation gap",
    },
    "L27": {
        "name": "Compliance",
        "criticality": "MEDIUM",
        "primary_threat": "FIPS drift / audit evasion",
    },
    "L28": {
        "name": "Audit / Non-Repudiation",
        "criticality": "HIGH",
        "primary_threat": "Timestamp forgery / log deletion",
    },
    "L29": {
        "name": "AI / ML Security",
        "criticality": "HIGH",
        "primary_threat": "Model poisoning / adversarial JWT",
    },
}


# ---------------------------------------------------------------------------
# Pre-seeded realistic metrics for key layers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)
_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _ts(delta_minutes: int = 0) -> str:
    return (_NOW - timedelta(minutes=delta_minutes)).strftime(_FMT)


_PRESET_METRICS: dict[str, dict[str, Any]] = {
    # L04 TLS — HNDL concern, 3 servers still on TLS 1.2
    "L04": {
        "health_score": 72,
        "status": "DEGRADED",
        "last_check_time": _ts(2),
        "uptime_percent": 99.1,
        "crypto_health": {
            "tls_1_0_servers": 0,
            "tls_1_1_servers": 0,
            "tls_1_2_servers": 3,   # HNDL risk
            "tls_1_3_servers": 14,
            "weak_cipher_count": 1,
            "pq_tls_servers": 0,
        },
        "alerts": [
            {
                "severity": "HIGH",
                "rule": "RULE-TLS-002",
                "message": "TLS 1.2 still active on 3 servers — HNDL (Harvest Now Decrypt Later) risk",
                "timestamp": _ts(35),
                "affected": ["api-gw-prod-02", "legacy-portal-01", "reporting-srv-03"],
            },
            {
                "severity": "MEDIUM",
                "rule": "RULE-TLS-003",
                "message": "Certificate api-gw-prod-02.example.com expires in 18 days",
                "timestamp": _ts(120),
                "affected": ["api-gw-prod-02"],
            },
            {
                "severity": "MEDIUM",
                "rule": "RULE-TLS-003",
                "message": "Certificate reporting-srv-03.example.com expires in 27 days",
                "timestamp": _ts(121),
                "affected": ["reporting-srv-03"],
            },
        ],
        "incidents": [
            {
                "id": "INC-TLS-2024-001",
                "description": "TLS 1.0 downgrade attempt detected on legacy-portal-01 (blocked)",
                "opened": _ts(72 * 60),
                "status": "RESOLVED",
            }
        ],
    },
    # L06 PKI — RSA-1024 in chain, 2 expiring certs
    "L06": {
        "health_score": 65,
        "status": "DEGRADED",
        "last_check_time": _ts(5),
        "uptime_percent": 99.9,
        "crypto_health": {
            "rsa_1024_certs": 1,    # CRITICAL — quantum-vulnerable + weak classical
            "rsa_2048_certs": 8,
            "rsa_4096_certs": 2,
            "ecdsa_p256_certs": 5,
            "expiring_within_30_days": 2,
            "expired_certs": 0,
            "ocsp_response_age_hours": 19,
        },
        "alerts": [
            {
                "severity": "CRITICAL",
                "rule": "RULE-PKI-001",
                "message": "RSA-1024 certificate detected in intermediate CA chain — immediate revocation required",
                "timestamp": _ts(14),
                "affected": ["int-ca-legacy-01"],
            },
            {
                "severity": "HIGH",
                "rule": "RULE-PKI-004",
                "message": "Root CA cert expires in 61 days — emergency renewal required",
                "timestamp": _ts(60),
                "affected": ["root-ca-01"],
            },
            {
                "severity": "MEDIUM",
                "rule": "RULE-PKI-003",
                "message": "cert-manager: 2 certs expiring within 30 days",
                "timestamp": _ts(180),
                "affected": ["svc-mesh-01.example.com", "int-api-02.example.com"],
            },
        ],
        "incidents": [],
    },
    # L08 JWT — RS256, one algorithm confusion event last week
    "L08": {
        "health_score": 80,
        "status": "WARNING",
        "last_check_time": _ts(3),
        "uptime_percent": 99.7,
        "crypto_health": {
            "jwt_algorithm": "RS256",
            "rs256_key_bits": 2048,
            "hs256_usage_count": 0,
            "alg_none_attempts_last_24h": 0,
            "algo_confusion_last_7d": 1,  # HS256 where RS256 expected
            "token_avg_exp_minutes": 60,
        },
        "alerts": [
            {
                "severity": "HIGH",
                "rule": "RULE-JWT-002",
                "message": "Algorithm confusion attempt detected: HS256 token presented to RS256 endpoint (blocked)",
                "timestamp": _ts(7 * 24 * 60 - 15),
                "affected": ["api-auth-service"],
            },
            {
                "severity": "LOW",
                "rule": "RULE-JWT-004",
                "message": "RS256 signing key age: 78 days — schedule rotation within 12 days",
                "timestamp": _ts(24 * 60),
                "affected": ["keycloak-prod"],
            },
        ],
        "incidents": [],
    },
    # L10 SSH — healthy but PQ KEX not enforced
    "L10": {
        "health_score": 90,
        "status": "HEALTHY",
        "last_check_time": _ts(1),
        "uptime_percent": 99.95,
        "crypto_health": {
            "openssh_version": "9.5",
            "hybrid_pq_kex_available": True,
            "hybrid_pq_kex_enforced": False,   # opportunity gap
            "rsa_4096_keys": 12,
            "ecdsa_keys": 8,
            "auth_fail_last_hour": 2,
            "fail2ban_bans_last_24h": 4,
        },
        "alerts": [
            {
                "severity": "INFORMATIONAL",
                "rule": "RULE-SSH-003",
                "message": "OpenSSH 9.5 supports hybrid PQ KEX (sntrup761x25519-sha512) but it is not enforced in sshd_config — enforce by Q3 2025",
                "timestamp": _ts(30 * 24 * 60),
                "affected": ["all SSH servers"],
            }
        ],
        "incidents": [],
    },
    # L18 Blockchain — CRITICAL: ECDSA exposed, $2.3M at risk
    "L18": {
        "health_score": 40,
        "status": "CRITICAL",
        "last_check_time": _ts(10),
        "uptime_percent": 100.0,  # chain is up, but quantum risk is extreme
        "crypto_health": {
            "ecdsa_algorithm": "secp256k1",
            "p2pk_outputs_detected": 47,        # public keys fully exposed
            "address_reuse_count": 112,          # each reuse exposes public key
            "wallet_balance_at_risk_usd": 2_300_000,
            "wallet_count_at_risk": 18,
            "shor_algorithm_break_timeline_years": "5-10 (CRQC estimate)",
            "quantum_safe_address_type_available": "P2TR (Taproot) — migration possible",
        },
        "alerts": [
            {
                "severity": "CRITICAL",
                "rule": "RULE-BC-001",
                "message": "47 P2PK outputs detected — public keys fully exposed on chain; vulnerable to Shor attack on CRQC",
                "timestamp": _ts(5),
                "affected": ["bitcoin-wallet-cluster", "ethereum-hot-wallet"],
            },
            {
                "severity": "CRITICAL",
                "rule": "RULE-BC-002",
                "message": "112 address reuse events — public keys exposed; $2.3M USD in wallets at quantum risk",
                "timestamp": _ts(6),
                "affected": ["eth-custody-01", "btc-custody-02", "16 additional wallets"],
            },
            {
                "severity": "HIGH",
                "rule": "RULE-BC-004",
                "message": "ECDSA secp256k1 has no quantum-safe upgrade path on Bitcoin mainnet — migrate to P2TR and monitor NIST PQC coin standards",
                "timestamp": _ts(7 * 24 * 60),
                "affected": ["all blockchain nodes"],
            },
        ],
        "incidents": [
            {
                "id": "INC-BC-2024-003",
                "description": "Emergency quantum-migration assessment initiated — $2.3M at risk in ECDSA P2PK outputs",
                "opened": _ts(30 * 24 * 60),
                "status": "IN_PROGRESS",
            }
        ],
    },
}


# ---------------------------------------------------------------------------
# Deterministic pseudo-random health generator for other layers
# ---------------------------------------------------------------------------

def _pseudo_health(layer_id: str) -> int:
    """Return a deterministic health score in 75-98 for non-preset layers."""
    digest = int(hashlib.md5(layer_id.encode()).hexdigest(), 16)
    return 75 + (digest % 24)  # 75-98


def _pseudo_status(score: int) -> str:
    if score >= 90:
        return "HEALTHY"
    if score >= 75:
        return "WARNING"
    return "DEGRADED"


# ---------------------------------------------------------------------------
# Attack simulation catalogue
# ---------------------------------------------------------------------------

_ATTACKS: dict[str, dict[str, Any]] = {
    "quantum_shor": {
        "description": "Cryptographically Relevant Quantum Computer (CRQC) executing Shor's algorithm",
        "impact_on_rsa": "RSA-2048 factored in ~8 hours (theoretical CRQC)",
        "impact_on_ecdsa": "secp256k1 private key recovered from public key",
        "impact_on_dh": "DH-2048 discrete log solved — VPN/TLS session keys exposed",
        "affected_layers": ["L01", "L03", "L04", "L06", "L07", "L08", "L09", "L10",
                            "L11", "L12", "L13", "L14", "L15", "L16", "L18", "L19",
                            "L22", "L23", "L26", "L28", "L29"],
        "severity": "CATASTROPHIC",
        "timeline": "5-15 years (CRQC estimate)",
    },
    "hndl": {
        "description": "Harvest Now Decrypt Later — adversary stores TLS ciphertext today for future CRQC decryption",
        "impact_on_rsa": "All RSA-encrypted TLS sessions retroactively decryptable",
        "impact_on_ecdsa": "ECDH key agreement sessions retroactively exposed",
        "severity": "CRITICAL",
        "timeline": "Happening now — harvest phase is passive",
    },
    "algorithm_confusion": {
        "description": "JWT algorithm confusion (RS256 → HS256) or alg=none attack",
        "impact": "JWT signature bypass — arbitrary token forgery",
        "affected_layers": ["L08", "L16"],
        "severity": "CRITICAL",
        "timeline": "Immediate — classical attack",
    },
    "cert_chain_weak_key": {
        "description": "RSA-1024 intermediate CA in trust chain",
        "impact": "Classical GNFS factorization feasible on modern hardware (~$1M compute)",
        "affected_layers": ["L04", "L06", "L07"],
        "severity": "CRITICAL",
        "timeline": "Feasible now with nation-state resources",
    },
    "ssh_brute_force": {
        "description": "Credential stuffing / SSH brute-force with leaked password lists",
        "impact": "Unauthorized shell access",
        "affected_layers": ["L10"],
        "severity": "HIGH",
        "timeline": "Immediate",
    },
    "blockchain_p2pk": {
        "description": "ECDSA secp256k1 Shor attack on exposed P2PK outputs",
        "impact": "Private key recovery → fund theft from ECDSA wallets",
        "affected_layers": ["L18"],
        "severity": "CATASTROPHIC",
        "timeline": "5-10 years (CRQC)",
    },
    "tls_downgrade": {
        "description": "POODLE / BEAST / DROWN-style TLS version downgrade",
        "impact": "Session decryption, cookie theft",
        "affected_layers": ["L04", "L07"],
        "severity": "HIGH",
        "timeline": "Immediate (if TLS < 1.2 still enabled)",
    },
    "dns_cache_poisoning": {
        "description": "Kaminsky-style DNS cache poisoning against unsigned zones",
        "impact": "Redirect legitimate traffic to attacker-controlled server",
        "affected_layers": ["L09"],
        "severity": "HIGH",
        "timeline": "Immediate",
    },
    "supply_chain_injection": {
        "description": "Malicious package substitution / build-pipeline injection",
        "impact": "Backdoored artefacts deployed to production",
        "affected_layers": ["L12", "L23"],
        "severity": "CRITICAL",
        "timeline": "Immediate",
    },
    "vault_seal": {
        "description": "Vault forced-seal via resource exhaustion / operator collusion",
        "impact": "All secrets inaccessible; potential plaintext key exposure during re-seal",
        "affected_layers": ["L14", "L26"],
        "severity": "CRITICAL",
        "timeline": "Immediate",
    },
}


# ---------------------------------------------------------------------------
# LayerMonitor class
# ---------------------------------------------------------------------------

class LayerMonitor:
    """Provides health metrics and attack simulations for all 29 security layers."""

    def __init__(self) -> None:
        self._registry = OSSRegistry()
        self._layers = {
            layer["layer_id"]: layer for layer in self._registry._layers
        }

    # ------------------------------------------------------------------
    # get_metrics
    # ------------------------------------------------------------------

    def get_metrics(self, layer_id: str) -> dict[str, Any]:
        """Return current monitoring metrics for *layer_id*.

        Returns preset realistic metrics for L04/L06/L08/L10/L18;
        generates deterministic pseudo-random metrics for all other layers.
        """
        lid = layer_id.upper()
        if lid not in _LAYER_META:
            return {"error": f"Unknown layer_id: {layer_id}"}

        meta = _LAYER_META[lid]
        layer_data = self._layers.get(lid, {})
        sw_list = layer_data.get("software", [])
        vuln_count = sum(1 for s in sw_list if s.get("quantum_vulnerable", False))

        # Preset data for key layers
        if lid in _PRESET_METRICS:
            base = dict(_PRESET_METRICS[lid])
        else:
            score = _pseudo_health(lid)
            base = {
                "health_score": score,
                "status": _pseudo_status(score),
                "last_check_time": _ts(5),
                "uptime_percent": round(99.0 + (score - 75) / 240, 2),
                "crypto_health": {
                    "note": "Detailed crypto telemetry not yet wired for this layer",
                    "quantum_vulnerable_packages": vuln_count,
                },
                "alerts": [],
                "incidents": [],
            }

        # Always augment with static layer context
        base.update(
            {
                "layer_id": lid,
                "layer_name": meta["name"],
                "criticality": meta["criticality"],
                "primary_threat": meta["primary_threat"],
                "software_count": len(sw_list),
                "quantum_vulnerable_packages": vuln_count,
                "monitoring_tools": layer_data.get("monitoring_tools", []),
            }
        )
        return base

    # ------------------------------------------------------------------
    # simulate_attack_on_layer
    # ------------------------------------------------------------------

    def simulate_attack_on_layer(
        self, layer_id: str, attack_type: str
    ) -> dict[str, Any]:
        """Return a before/after attack simulation for *layer_id*.

        Parameters
        ----------
        layer_id : str
            e.g. "L04", "L18"
        attack_type : str
            One of the keys in the _ATTACKS catalogue:
            quantum_shor, hndl, algorithm_confusion, cert_chain_weak_key,
            ssh_brute_force, blockchain_p2pk, tls_downgrade,
            dns_cache_poisoning, supply_chain_injection, vault_seal

        Returns
        -------
        dict with keys: layer_id, attack_type, attack_description,
                        severity, before_attack, after_attack, impact_summary,
                        recommended_mitigations
        """
        lid = layer_id.upper()
        if lid not in _LAYER_META:
            return {"error": f"Unknown layer_id: {layer_id}"}

        attack = _ATTACKS.get(
            attack_type.lower(),
            {
                "description": f"Unknown attack type: {attack_type}",
                "severity": "UNKNOWN",
            },
        )

        before = self.get_metrics(lid)

        # Simulate degraded state post-attack
        before_score = before.get("health_score", 80)

        # Impact magnitude varies by attack type and layer criticality
        severity = attack.get("severity", "HIGH")
        drop: dict[str, int] = {
            "CATASTROPHIC": 70,
            "CRITICAL": 50,
            "HIGH": 30,
            "MEDIUM": 15,
            "LOW": 5,
        }
        score_drop = drop.get(severity, 20)

        after_score = max(0, before_score - score_drop)
        after_status = (
            "COMPROMISED"
            if after_score < 20
            else ("CRITICAL" if after_score < 40 else "DEGRADED")
        )

        # Construct plausible post-attack alerts
        after_alerts = list(before.get("alerts", [])) + [
            {
                "severity": severity if severity != "CATASTROPHIC" else "CRITICAL",
                "rule": f"RULE-ATTACK-{lid}-001",
                "message": f"ATTACK DETECTED: {attack.get('description', attack_type)} on {lid}",
                "timestamp": _ts(0),
                "affected": [_LAYER_META[lid]["name"]],
            }
        ]

        after_incidents = list(before.get("incidents", [])) + [
            {
                "id": f"INC-{lid}-ATK-{attack_type.upper()}",
                "description": attack.get("description", attack_type),
                "opened": _ts(0),
                "status": "ACTIVE",
            }
        ]

        after = {
            "health_score": after_score,
            "status": after_status,
            "last_check_time": _ts(0),
            "uptime_percent": max(0.0, before.get("uptime_percent", 99.0) - (score_drop / 10)),
            "crypto_health": before.get("crypto_health", {}),
            "alerts": after_alerts,
            "incidents": after_incidents,
        }

        # Recommended mitigations per attack type
        mitigations: dict[str, list[str]] = {
            "quantum_shor": [
                "Migrate all asymmetric algorithms to NIST FIPS 203/204/205 (ML-KEM, ML-DSA, SLH-DSA)",
                "Enable TLS hybrid PQ key exchange (X25519Kyber768) as first migration step",
                "Rotate all RSA/ECDSA keys immediately once CRQC threat materialises",
                "Prioritise L18 (Blockchain) and L06 (PKI) — highest blast radius",
            ],
            "hndl": [
                "Deploy TLS 1.3 with hybrid PQ KEM on all public endpoints immediately",
                "Disable TLS 1.2 on all servers within 90 days",
                "Implement perfect-forward-secrecy (PFS) ciphers only",
                "Log and inventory all externally-captured TLS traffic for retroactive risk assessment",
            ],
            "algorithm_confusion": [
                "Enforce strict algorithm allow-list in JWT validation (reject HS256 on RS256 endpoints)",
                "Never use the same key for both symmetric and asymmetric JWT algorithms",
                "Upgrade python-jose to latest; enable strict algorithm validation flag",
            ],
            "cert_chain_weak_key": [
                "Revoke and reissue all certificates signed by RSA-1024 intermediate CA immediately",
                "Enforce minimum RSA-2048 / P-256 in cert-manager policy",
                "Run weekly OpenSSL chain verification scan",
            ],
            "ssh_brute_force": [
                "Enforce fail2ban with 3-strike / 1-hour ban",
                "Require hardware-key (FIDO2) or certificate-based SSH authentication",
                "Disable password authentication in sshd_config",
            ],
            "blockchain_p2pk": [
                "Migrate all P2PK outputs to P2WPKH or P2TR (Taproot) spend paths",
                "Never reuse Bitcoin/Ethereum addresses",
                "Monitor NIST post-quantum standards for blockchain applicability",
                "Consider holding reserves in cold-storage P2TR addresses",
            ],
            "tls_downgrade": [
                "Disable TLS 1.0 and 1.1 on all endpoints immediately",
                "Set SSLProtocol TLSv1.2 TLSv1.3 minimum in nginx/Apache config",
                "Enable HSTS with 2-year max-age + includeSubDomains",
            ],
            "dns_cache_poisoning": [
                "Enable DNSSEC signing on all authoritative zones",
                "Enable DNSSEC validation on all resolvers",
                "Use DNS-over-TLS (DoT) or DNS-over-HTTPS (DoH) for stub resolvers",
            ],
            "supply_chain_injection": [
                "Enforce cosign signature verification on all OCI image admissions",
                "Pin all build dependencies to cryptographic hashes (SHA-256)",
                "Require in-toto attestation for all CI/CD pipeline steps",
                "Scan with Trivy + Syft on every PR merge",
            ],
            "vault_seal": [
                "Enable Vault auto-unseal via cloud KMS (AWS KMS / GCP CKMS)",
                "Require quorum (Shamir threshold N-of-M) for manual unseal operations",
                "Alert on-call immediately on unexpected seal event",
                "Regularly test unseal recovery runbook",
            ],
        }

        return {
            "layer_id": lid,
            "layer_name": _LAYER_META[lid]["name"],
            "attack_type": attack_type,
            "attack_description": attack.get("description", attack_type),
            "attack_severity": severity,
            "before_attack": {
                "health_score": before_score,
                "status": before.get("status", "HEALTHY"),
                "alert_count": len(before.get("alerts", [])),
                "open_incidents": len(
                    [i for i in before.get("incidents", []) if i.get("status") != "RESOLVED"]
                ),
            },
            "after_attack": {
                "health_score": after_score,
                "status": after_status,
                "alert_count": len(after["alerts"]),
                "open_incidents": len(after["incidents"]),
            },
            "health_score_drop": before_score - after_score,
            "impact_summary": attack.get(
                "impact",
                attack.get("impact_on_rsa", attack.get("description", "Layer compromised")),
            ),
            "recommended_mitigations": mitigations.get(attack_type.lower(), [
                "Apply vendor security patch immediately",
                "Rotate all keys and certificates on affected layer",
                "Engage incident response process",
            ]),
        }

    # ------------------------------------------------------------------
    # get_all_layer_health
    # ------------------------------------------------------------------

    def get_all_layer_health(self) -> list[dict[str, Any]]:
        """Return health summaries for all 29 security layers.

        Each entry contains: layer_id, layer_name, criticality,
        health_score, status, alert_count, open_incident_count,
        quantum_vulnerable_packages.
        """
        summaries: list[dict[str, Any]] = []
        for lid in sorted(_LAYER_META.keys()):
            m = self.get_metrics(lid)
            summaries.append(
                {
                    "layer_id": lid,
                    "layer_name": m.get("layer_name", ""),
                    "criticality": m.get("criticality", ""),
                    "health_score": m.get("health_score", 0),
                    "status": m.get("status", "UNKNOWN"),
                    "alert_count": len(m.get("alerts", [])),
                    "open_incident_count": len(
                        [
                            i
                            for i in m.get("incidents", [])
                            if i.get("status") != "RESOLVED"
                        ]
                    ),
                    "quantum_vulnerable_packages": m.get("quantum_vulnerable_packages", 0),
                }
            )
        return summaries


# ---------------------------------------------------------------------------
# main — full monitoring dashboard
# ---------------------------------------------------------------------------

def _health_bar(score: int, width: int = 20) -> str:
    filled = int(score / 100 * width)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {score:3d}"


def _status_label(status: str) -> str:
    labels = {
        "HEALTHY": "  OK  ",
        "WARNING": " WARN ",
        "DEGRADED": "DEGR  ",
        "CRITICAL": "CRIT! ",
        "COMPROMISED": "COMPR!",
    }
    return labels.get(status, status[:6].upper())


def main() -> None:
    monitor = LayerMonitor()

    print("=" * 72)
    print("CLASSICAL SECURITY LAB — LAYER MONITORING DASHBOARD")
    print(f"Generated: {_NOW.strftime(_FMT)}")
    print("=" * 72)

    all_health = monitor.get_all_layer_health()

    # Overall stats
    scores = [h["health_score"] for h in all_health]
    avg_score = round(sum(scores) / len(scores), 1)
    critical_layers = [h for h in all_health if h["status"] in ("CRITICAL", "COMPROMISED")]
    warning_layers = [h for h in all_health if h["status"] in ("WARNING", "DEGRADED")]
    total_alerts = sum(h["alert_count"] for h in all_health)
    total_incidents = sum(h["open_incident_count"] for h in all_health)
    total_vuln_packages = sum(h["quantum_vulnerable_packages"] for h in all_health)

    print(f"\n  Layers monitored    : 29")
    print(f"  Average health score: {avg_score}/100")
    print(f"  Critical/Compromised: {len(critical_layers)}")
    print(f"  Warning/Degraded    : {len(warning_layers)}")
    print(f"  Open alerts         : {total_alerts}")
    print(f"  Active incidents    : {total_incidents}")
    print(f"  Quantum-vuln pkgs   : {total_vuln_packages} (across all layers)")

    # Layer table
    print("\n" + "-" * 72)
    print(
        f"  {'Layer':<6} {'Status':<8} {'Health':<26} {'Alerts':>6} {'Incidents':>10}"
        f"  {'Layer Name'}"
    )
    print("-" * 72)

    for h in all_health:
        status_str = _status_label(h["status"])
        bar_str = _health_bar(h["health_score"])
        print(
            f"  {h['layer_id']:<6} {status_str:<8} {bar_str:<26}"
            f" {h['alert_count']:>6} {h['open_incident_count']:>10}"
            f"  {h['layer_name']}"
        )

    print("-" * 72)

    # Active alerts summary
    print("\n--- Active Alerts (all layers) ---")
    for lid in sorted(_LAYER_META.keys()):
        metrics = monitor.get_metrics(lid)
        alerts = metrics.get("alerts", [])
        if alerts:
            for alert in alerts:
                sev = alert.get("severity", "?")
                msg = alert.get("message", "")
                rule = alert.get("rule", "")
                print(f"  [{lid}] [{sev:<13}] {rule:<18} {msg[:65]}")

    # Open incidents summary
    print("\n--- Open Incidents ---")
    any_incidents = False
    for lid in sorted(_LAYER_META.keys()):
        metrics = monitor.get_metrics(lid)
        for inc in metrics.get("incidents", []):
            if inc.get("status") != "RESOLVED":
                any_incidents = True
                print(
                    f"  [{lid}] [{inc['status']:<12}] {inc['id']:<30}"
                    f" {inc['description'][:55]}"
                )
    if not any_incidents:
        print("  No open incidents.")

    # Attack simulation: Shor on L18
    print("\n--- Attack Simulation: Shor's Algorithm on L18 Blockchain ---")
    sim = monitor.simulate_attack_on_layer("L18", "quantum_shor")
    print(
        f"  Before: health={sim['before_attack']['health_score']}"
        f"  status={sim['before_attack']['status']}"
    )
    print(
        f"  After : health={sim['after_attack']['health_score']}"
        f"  status={sim['after_attack']['status']}"
    )
    print(f"  Score drop: {sim['health_score_drop']} points")
    print(f"  Impact    : {sim['impact_summary']}")
    print("  Mitigations:")
    for m in sim["recommended_mitigations"][:3]:
        print(f"    - {m}")

    # Attack simulation: HNDL on L04
    print("\n--- Attack Simulation: HNDL on L04 TLS ---")
    sim2 = monitor.simulate_attack_on_layer("L04", "hndl")
    print(
        f"  Before: health={sim2['before_attack']['health_score']}"
        f"  status={sim2['before_attack']['status']}"
    )
    print(
        f"  After : health={sim2['after_attack']['health_score']}"
        f"  status={sim2['after_attack']['status']}"
    )
    print(f"  Score drop: {sim2['health_score_drop']} points")
    print(f"  Impact    : {sim2['impact_summary']}")

    print("\n" + "=" * 72)
    print("DASHBOARD COMPLETE")
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()
