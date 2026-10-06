"""
Quantum Security Maturity Model (QSMM) — 29-layer assessment
=============================================================
Version : 1.0
Date    : 2026-10-01
Author  : Quantum Security Lab

Five-level QSMM:
  L0 Unaware   — No awareness of quantum threat
  L1 Aware     — Inventory started, no migration plan
  L2 Assessed  — Full CBOM, risk assessed, plan drafted
  L3 Migrating — Hybrid deployed, PQC testing in progress
  L4 Migrated  — PQC live, old algorithms removed, monitoring
  L5 Optimized — Crypto agility, automated rotation, continuous compliance
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


# ─── Data model ──────────────────────────────────────────────────────────────

@dataclass
class LayerMaturity:
    layer_id: str
    layer_name: str
    current_level: int          # 0-5
    justification: str
    sub_scores: dict[str, int]  # 6 dimensions, each 0-5
    gaps: list[str]
    next_steps: list[str]
    effort_to_next_level: str
    blocking_dependencies: list[str]

    @property
    def average_score(self) -> float:
        if not self.sub_scores:
            return 0.0
        return round(sum(self.sub_scores.values()) / len(self.sub_scores), 2)

    @property
    def level_badge(self) -> str:
        labels = {
            0: "L0 UNAWARE",
            1: "L1 AWARE",
            2: "L2 ASSESSED",
            3: "L3 MIGRATING",
            4: "L4 MIGRATED",
            5: "L5 OPTIMIZED",
        }
        return labels.get(self.current_level, "UNKNOWN")


# ─── Raw layer definitions ────────────────────────────────────────────────────

_RAW_LAYERS: list[dict[str, Any]] = [
    {
        "layer_id": "L01",
        "layer_name": "Physical / Hardware",
        "current_level": 1,
        "justification": (
            "Hardware entropy sources inventoried at OS level but no QRNG deployed. "
            "TPM 2.0 in use; TPM 3.0 (NIST SP 800-90C) unavailable. Hardware crypto "
            "inventory partial — FPGAs and HSM cards not CBOMed."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  1,
            "migration_plan":   1,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "QRNG (NIST SP 800-90C compliant) not procured or deployed",
            "TPM 3.0 firmware not available; TPM 2.0 lacks PQC key-storage primitives",
            "Hardware crypto inventory incomplete — FPGAs, SmartNICs not in CBOM",
            "No entropy-health monitoring for PRNG seeding",
        ],
        "next_steps": [
            "Add hardware RNG sources (FPGA, HSM) to CBOM toolchain",
            "Evaluate TPM 3.0 roadmap with hardware vendors",
            "Baseline entropy quality with NIST SP 800-90B test suite",
            "Tag physical HSM cards in crypto inventory",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": [],
    },
    {
        "layer_id": "L02",
        "layer_name": "Data Link / MACsec",
        "current_level": 1,
        "justification": (
            "MACsec 802.1AE deployed on core switches with AES-256-GCM (safe). "
            "However EAP-TLS SAK distribution uses RSA-2048 certificates — vulnerable "
            "to Shor's. No PQC MACsec KEX plan documented."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  2,
            "migration_plan":   1,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "EAP-TLS mutual auth uses RSA-2048 certificates — Shor's breaks key exchange",
            "No PQC MACsec SAK distribution plan (IEEE 802.1AE PQC extension not evaluated)",
            "MACsec coverage map incomplete — 3 switch closets unmapped",
            "No automated cert-expiry monitoring for MACsec EAP certs",
        ],
        "next_steps": [
            "Inventory all MACsec-enabled interfaces and their certificate chain",
            "Draft migration plan: EAP-TLS ➜ ML-DSA-65 certificates",
            "Evaluate IEEE 802.1AE PQC working-group drafts",
            "Deploy cert-expiry alerts for MACsec EAP certificates",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L06 (PKI must issue ML-DSA certs first)"],
    },
    {
        "layer_id": "L03",
        "layer_name": "Network / IPsec",
        "current_level": 1,
        "justification": (
            "IPsec IKEv2 tunnels inventoried (8 tunnels identified, DH-2048 confirmed). "
            "HNDL risk documented in threat model. RFC 9242 / RFC 9370 hybrid KEX not "
            "implemented. Migration plan draft exists but not approved."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "DH Group 14 (2048-bit) active on all 8 IKEv2 tunnels — breakable by Shor's",
            "RFC 9242 (ML-KEM in IKEv2) not implemented; RFC 9370 hybrid not available",
            "IKEv2 PQC extension requires StrongSwan ≥ 5.9.11 — kernel not updated",
            "HNDL: nation-state adversaries archiving IPsec ciphertext today",
        ],
        "next_steps": [
            "Upgrade StrongSwan to ≥ 5.9.11 on all VPN gateways",
            "Enable RFC 9370 hybrid KEX (ML-KEM-1024 + DH Group 14) as hybrid phase",
            "Approve and publish IPsec PQC migration plan",
            "Add IKEv2 SA algorithm telemetry to SIEM dashboard",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L14 (HSM must wrap new IKEv2 pre-shared keys)"],
    },
    {
        "layer_id": "L04",
        "layer_name": "TLS Transport",
        "current_level": 2,
        "justification": (
            "Full CBOM of TLS endpoints completed (847 certs inventoried). Risk "
            "assessment scores HNDL at CRITICAL. Migration plan drafted: hybrid "
            "X25519+ML-KEM-768 per IETF draft-ietf-tls-hybrid-design. Tooling "
            "gap: OpenSSL 3.3 + OQS provider not yet in production nginx."
        ),
        "sub_scores": {
            "crypto_inventory": 4,
            "risk_assessment":  4,
            "migration_plan":   3,
            "tooling":          2,
            "monitoring":       3,
            "compliance":       2,
        },
        "gaps": [
            "Hybrid TLS (X25519+ML-KEM-768) not deployed — IETF draft not in OpenSSL build",
            "nginx production build lacks OQS provider — PQC ciphers unavailable",
            "HNDL risk active: all TLS 1.3 sessions archivable by CRQC adversary",
            "847 TLS certificates not yet re-issued as hybrid certs",
            "No automated cipher-suite scanning against CNSA 2.0 TLS requirements",
        ],
        "next_steps": [
            "Build nginx with OpenSSL 3.3 + OQS provider in staging",
            "Enable X25519MLKEM768 cipher in TLS config (hybrid mode)",
            "Re-issue top-25 highest-risk certs as ML-DSA-65 hybrid",
            "Add TLS cipher-suite telemetry to SIEM (flag RSA/ECDHE usage)",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L06 (PKI must issue ML-DSA certs)", "L14 (HSM must support ML-KEM)"],
    },
    {
        "layer_id": "L05",
        "layer_name": "Session",
        "current_level": 1,
        "justification": (
            "TLS session tickets use RSA-2048 encryption for ticket key transport. "
            "Session ticket lifetime audited but key rotation is manual. No PQC "
            "session ticket standard exists yet (IETF WG in progress)."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  2,
            "migration_plan":   1,
            "tooling":          1,
            "monitoring":       1,
            "compliance":       1,
        },
        "gaps": [
            "RSA-2048 wraps session ticket encryption keys — recoverable post-CRQC",
            "Session ticket key rotation is manual (quarterly) — should be daily",
            "No IETF standard for PQC session ticket encryption yet",
            "Session resumption audit not automated",
        ],
        "next_steps": [
            "Disable TLS session tickets; rely on session IDs with PQC-safe storage",
            "Automate session ticket key rotation (daily) as interim measure",
            "Track IETF TLS WG draft on PQC session ticket encryption",
            "Add session-ticket key-algorithm monitoring to dashboard",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": ["L04 (TLS layer must migrate first)"],
    },
    {
        "layer_id": "L06",
        "layer_name": "X.509 PKI",
        "current_level": 2,
        "justification": (
            "CBOM of certificate inventory complete (847 certs, 3 CAs). Risk "
            "assessment complete — CRITICAL on RSA-1024 legacy certs. Migration "
            "plan drafted to ML-DSA-65 (FIPS 204). cert-manager not configured "
            "for PQC issuance. No ML-DSA CA operational."
        ),
        "sub_scores": {
            "crypto_inventory": 4,
            "risk_assessment":  4,
            "migration_plan":   3,
            "tooling":          2,
            "monitoring":       3,
            "compliance":       2,
        },
        "gaps": [
            "No ML-DSA-65 (FIPS 204) CA deployed — Issuing CA still RSA-2048",
            "RSA-1024 legacy cert found in chain (expired but not revoked)",
            "cert-manager PQC issuer plugin not configured",
            "Dual-algorithm (hybrid) cert issuance workflow not tested",
            "CRL/OCSP endpoints not tested with ML-DSA-signed responses",
        ],
        "next_steps": [
            "Stand up ML-DSA-65 sub-CA in offline PKI (Step CA or EJBCA)",
            "Revoke and remove RSA-1024 legacy cert from chain immediately",
            "Configure cert-manager with PQC issuer for Kubernetes workloads",
            "Test hybrid cert (RSA + ML-DSA) issuance and browser compatibility",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L14 (HSM must store ML-DSA root key)"],
    },
    {
        "layer_id": "L07",
        "layer_name": "HTTPS",
        "current_level": 2,
        "justification": (
            "HTTPS deployed across all public endpoints. TLS cert inventory complete. "
            "HSTS, OCSP stapling enabled. Migration depends entirely on L04 TLS and "
            "L06 PKI — no independent PQC HTTPS work possible until those layers "
            "advance."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          2,
            "monitoring":       3,
            "compliance":       2,
        },
        "gaps": [
            "HTTPS cipher-suite PQC readiness blocked by L04 TLS migration",
            "HSTS headers present but cert chain still RSA — PQC cert switch needed",
            "Public-facing APIs not tested with ML-KEM hybrid key exchange",
        ],
        "next_steps": [
            "Complete L04 and L06 migrations first",
            "Update HSTS preload list after PQC cert rollout",
            "Test all public HTTPS endpoints with Hybrid TLS client (pq-curl)",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": ["L04 (TLS)", "L06 (PKI)"],
    },
    {
        "layer_id": "L08",
        "layer_name": "JWT / Auth Tokens",
        "current_level": 1,
        "justification": (
            "47 microservices use RS256 JWT. Token issuer (Keycloak) uses RSA-2048 "
            "signing key. JOSE PQC JWT draft (draft-ietf-jose-pqc) not evaluated. "
            "No dual-algorithm issuer deployed. Token rotation policy documented but "
            "not quantum-aware."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "RS256 (RSA-2048) JWT signing on 47 microservices — all tokens forgeable post-CRQC",
            "No JOSE PQC algorithm (ML-DSA alg ID) implemented",
            "Keycloak has no PQC signing key option in current version",
            "Dual-token issuer (RS256 + ML-DSA parallel) not deployed",
            "Token-signing key rotation manual and infrequent",
        ],
        "next_steps": [
            "Inventory all JWT consumers and their algorithm acceptance",
            "Track IETF JOSE PQC draft for ML-DSA algorithm identifier",
            "Stand up Keycloak fork or sidecar with ML-DSA signing capability",
            "Define dual-issuer rollout plan (RS256 fallback + ML-DSA primary)",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L06 (PKI for signing key cert)", "L15 (IAM layer migration)"],
    },
    {
        "layer_id": "L09",
        "layer_name": "DNS / DNSSEC",
        "current_level": 1,
        "justification": (
            "DNSSEC deployed with RSA-2048 ZSK and KSK. Key rollover overdue by "
            "8 months. IETF PQC DNSSEC draft (draft-ietf-dnsop-dnssec-pqc) not "
            "evaluated. BIND 9.19 has experimental ML-DSA support not yet tested."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  2,
            "migration_plan":   1,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "DNSSEC ZSK RSA-2048 — key rollover overdue (last rolled 8 months ago)",
            "KSK RSA-2048 with 2-year lifetime — HNDL window wide open",
            "IETF PQC DNSSEC draft not evaluated; BIND 9.19 ML-DSA not tested",
            "No automated DNSSEC key rollover pipeline",
        ],
        "next_steps": [
            "Perform immediate ZSK rollover (overdue — do this week)",
            "Evaluate BIND 9.19 experimental ML-DSA DNSSEC support in lab",
            "Track IETF dnsop PQC DNSSEC draft for standardization timeline",
            "Automate ZSK/KSK rollover with dnssec-policy in BIND",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": [],
    },
    {
        "layer_id": "L10",
        "layer_name": "SSH",
        "current_level": 3,
        "justification": (
            "OpenSSH 9.0+ deployed across all servers. sntrup761 (ML-KEM equivalent) "
            "KEX available but not enforced in sshd_config. RSA host keys still "
            "present in authorized_keys on legacy jump hosts. Ed25519 user keys "
            "predominant (safe against Grover but not Shor's for 256-bit)."
        ),
        "sub_scores": {
            "crypto_inventory": 4,
            "risk_assessment":  4,
            "migration_plan":   4,
            "tooling":          4,
            "monitoring":       3,
            "compliance":       3,
        },
        "gaps": [
            "sntrup761 KEX available but not set as preferred — RSA KEX still negotiated",
            "RSA host keys present in authorized_keys on 14 legacy jump hosts",
            "sshd_config KexAlgorithms not restricted to PQC-safe algorithms",
            "SSH key rotation policy not automated",
        ],
        "next_steps": [
            "Set KexAlgorithms sntrup761x25519-sha512@openssh.com first in sshd_config",
            "Audit and remove RSA host keys from authorized_keys (14 jump hosts)",
            "Deploy SSH key rotation automation via Vault SSH secrets engine",
            "Validate all SSH connections use hybrid KEX via SIEM telemetry",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": [],
    },
    {
        "layer_id": "L11",
        "layer_name": "Email Security",
        "current_level": 0,
        "justification": (
            "PGP RSA-4096 keys in use for encrypted email with no migration plan. "
            "S/MIME RSA certs on all corporate mail clients. OpenPGP PQC draft "
            "(draft-ietf-openpgp-pqc) not evaluated. DKIM RSA-2048 signatures. "
            "No stakeholder awareness of email quantum risk."
        ),
        "sub_scores": {
            "crypto_inventory": 1,
            "risk_assessment":  1,
            "migration_plan":   0,
            "tooling":          0,
            "monitoring":       1,
            "compliance":       0,
        },
        "gaps": [
            "PGP RSA-4096 keys: no migration plan, no awareness of IETF PQC OpenPGP draft",
            "S/MIME RSA certs on all corporate mail clients — no PQC path documented",
            "DKIM RSA-2048 signatures — archived emails retroactively forgeable",
            "OpenPGP PQC draft (ML-KEM + ML-DSA hybrid) not evaluated by any team member",
            "No crypto inventory of email signing/encryption keys",
        ],
        "next_steps": [
            "Inventory all PGP/S-MIME keys and their algorithms immediately",
            "Assign email security owner to track IETF OpenPGP PQC draft",
            "Evaluate DKIM RSA → Ed25519 as interim step (Grover-safe)",
            "Draft email encryption migration plan (PGP ➜ ML-KEM + ML-DSA hybrid)",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": [],
    },
    {
        "layer_id": "L12",
        "layer_name": "Code Signing",
        "current_level": 1,
        "justification": (
            "GPG RSA commit signing on main branch. cosign ECDSA P-256 for container "
            "image signing. Sigstore rekor transparency log used. ML-DSA signing "
            "not configured in any pipeline. Code signing inventory partially complete."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  2,
            "migration_plan":   1,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "GPG RSA commit signing — all historical commits forgeable post-CRQC",
            "cosign ECDSA P-256 container image signatures — Shor's breaks verification",
            "No ML-DSA signing key configured in GitHub Actions or cosign",
            "Sigstore community has no ML-DSA support in GA release yet",
        ],
        "next_steps": [
            "Switch GPG commit signing to Ed25519 keys (interim Grover-safe step)",
            "Track cosign / Sigstore ML-DSA support roadmap",
            "Evaluate notation (CNCF) for ML-DSA artifact signing",
            "Document code signing migration plan with timeline",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": [],
    },
    {
        "layer_id": "L13",
        "layer_name": "VPN",
        "current_level": 1,
        "justification": (
            "WireGuard (Curve25519) deployed for site-to-site VPN. OpenVPN for "
            "remote access. 8 IKEv2 site-to-site tunnels (DH-2048). No PQC patch "
            "for WireGuard (PQWG fork experimental). No hybrid TLS in OpenVPN."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "WireGuard Curve25519: no production PQC patch (pq-wireguard experimental)",
            "OpenVPN: no hybrid TLS mode deployed, uses TLS 1.2 with ECDHE",
            "8 IKEv2 tunnels using DH-2048 — see also L03 IPsec",
            "VPN server certificates RSA-2048 — blocked by L06 PKI migration",
        ],
        "next_steps": [
            "Evaluate pq-wireguard fork in isolated test environment",
            "Upgrade OpenVPN to 2.6.x and enable hybrid TLS 1.3 mode",
            "Migrate IKEv2 tunnels as part of L03 IPsec work (share effort)",
            "Monitor WireGuard upstream for official PQC KEX support",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L03 (IPsec)", "L06 (PKI certs)"],
    },
    {
        "layer_id": "L14",
        "layer_name": "HSM / KMS",
        "current_level": 2,
        "justification": (
            "HashiCorp Vault deployed as KMS. 847 DEKs wrapped with RSA-OAEP-2048. "
            "Migration plan drafted (Vault Transit ➜ ML-KEM wrapping). No FIPS 140-3 "
            "Level 3 HSM procured. Vault Enterprise license covers Transit but PQC "
            "plugin not GA."
        ),
        "sub_scores": {
            "crypto_inventory": 4,
            "risk_assessment":  4,
            "migration_plan":   3,
            "tooling":          2,
            "monitoring":       3,
            "compliance":       2,
        },
        "gaps": [
            "Vault RSA-OAEP wrapping 847 DEKs — all recoverable post-CRQC",
            "No FIPS 140-3 Level 3 hardware HSM procured (currently software-only)",
            "Vault Transit PQC plugin not GA — only available as community preview",
            "DEK rotation under ML-KEM not tested end-to-end",
            "Vault audit logs do not flag RSA-wrapped key operations",
        ],
        "next_steps": [
            "Issue RFP / procurement for FIPS 140-3 Level 3 HSM (Thales Luna / Entrust)",
            "Deploy Vault Transit PQC plugin in staging and test ML-KEM wrapping",
            "Rotate top-100 highest-value DEKs to ML-KEM wrapping as pilot",
            "Add RSA-wrapped key count metric to security dashboard",
        ],
        "effort_to_next_level": "6 months",
        "blocking_dependencies": ["L01 (hardware HSM)"],
    },
    {
        "layer_id": "L15",
        "layer_name": "Identity / IAM",
        "current_level": 1,
        "justification": (
            "Keycloak OIDC uses RS256 (RSA-2048) signing. SAML assertions RSA-signed. "
            "Kerberos PKINIT uses RSA certificates. No PQC OIDC profile standardised. "
            "Identity is the highest-leverage layer — migrating here unlocks L08 JWT."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "Keycloak RS256 OIDC: signing key RSA-2048, no PQC algorithm configured",
            "SAML RSA XML signatures on all federation assertions",
            "Kerberos PKINIT RSA-2048 — compromises enterprise authentication",
            "No PQC OIDC profile in IETF / OpenID Foundation yet",
            "SCIM provisioning tokens use RS256 JWTs",
        ],
        "next_steps": [
            "Upgrade Keycloak to 24+ and evaluate PQC signing key support",
            "Replace SAML federation with OIDC where possible (fewer PQC dependencies)",
            "Track IETF OAuth/OIDC PQC profile drafts",
            "Document IAM crypto-algorithm inventory in CBOM",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L06 (PKI for identity certs)", "L14 (KMS for signing keys)"],
    },
    {
        "layer_id": "L16",
        "layer_name": "API Security",
        "current_level": 1,
        "justification": (
            "47 microservices use JWT RS256 and mTLS with ECDSA P-256. API gateway "
            "(Kong) authenticates with RS256 tokens. No ML-DSA JWT deployed. "
            "mTLS certificates blocked by L06 PKI migration."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       3,
            "compliance":       1,
        },
        "gaps": [
            "JWT RS256 on 47 microservices — all token authenticity forgeable",
            "mTLS ECDSA P-256 certs on service mesh — Shor's breaks mutual auth",
            "API gateway (Kong) has no ML-DSA JWT verification plugin",
            "No ML-DSA JWT deployed on any endpoint",
        ],
        "next_steps": [
            "Inventory all API gateway JWT verification configs",
            "Test Kong ML-DSA JWT plugin (community) in staging",
            "Re-issue mTLS certs as hybrid as part of L19 service mesh migration",
            "Add API token algorithm telemetry to SIEM",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L08 (JWT)", "L06 (PKI)", "L19 (service mesh certs)"],
    },
    {
        "layer_id": "L17",
        "layer_name": "Database Encryption",
        "current_level": 2,
        "justification": (
            "PostgreSQL TDE via AES-256 (safe). MongoDB encrypted storage. Backup "
            "encryption key wrapped with RSA-2048 — HNDL risk on backups. DB "
            "connection TLS uses RSA cert. Migration plan approved for backup key "
            "wrapping."
        ),
        "sub_scores": {
            "crypto_inventory": 4,
            "risk_assessment":  3,
            "migration_plan":   3,
            "tooling":          3,
            "monitoring":       3,
            "compliance":       2,
        },
        "gaps": [
            "Backup encryption key wrapped with RSA-2048 — backups decryptable post-CRQC",
            "DB connection TLS cert RSA — blocked by L04 TLS and L06 PKI migration",
            "MongoDB field-level encryption uses ECDH key derivation",
            "Long-term backup retention (7 years) amplifies HNDL risk for PII",
        ],
        "next_steps": [
            "Re-wrap backup encryption keys with ML-KEM via Vault Transit pilot",
            "Migrate DB TLS certs as part of L06 PKI rollout",
            "Evaluate MongoDB CSFLE with ML-KEM key provider",
            "Document data-at-rest encryption in CBOM with retention tags",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L14 (KMS)", "L06 (PKI for TLS certs)"],
    },
    {
        "layer_id": "L18",
        "layer_name": "Blockchain / DLT",
        "current_level": 0,
        "justification": (
            "Production blockchain (Ethereum-compatible) uses ECDSA secp256k1 for "
            "wallet signing. $2.3M in on-chain assets. No PQC wallet solution "
            "evaluated. EIP PQC wallet proposal not tracked. No owner assigned "
            "for quantum risk."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  2,
            "migration_plan":   0,
            "tooling":          0,
            "monitoring":       1,
            "compliance":       0,
        },
        "gaps": [
            "ECDSA secp256k1 wallet keys — all $2.3M in assets at retroactive risk",
            "No PQC wallet solution deployed or even evaluated",
            "No EIP tracking for PQC address scheme (lattice-based or SLH-DSA)",
            "Smart contract upgrade mechanism not assessed for key-migration support",
            "No quantum risk owner assigned for blockchain assets",
        ],
        "next_steps": [
            "Assign quantum risk owner for blockchain/wallet assets immediately",
            "Track EIP proposals for PQC wallet address schemes",
            "Evaluate multi-sig cold-storage as interim risk mitigation",
            "Assess smart contract upgrade pattern for key rotation capability",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": [],
    },
    {
        "layer_id": "L19",
        "layer_name": "Container / Service Mesh",
        "current_level": 1,
        "justification": (
            "Istio mTLS on all 340 services using ECDSA P-256 SPIFFE SVIDs. SPIRE "
            "issues ECDSA certs. No PQC SPIFFE extension in production. "
            "OPA policies enforce mTLS but not algorithm requirements."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       3,
            "compliance":       1,
        },
        "gaps": [
            "Istio mTLS ECDSA on all 340 services — Shor's breaks all inter-service auth",
            "SPIRE ECDSA SVIDs: SVID rotation automated but algorithm still ECDSA",
            "No PQC SPIFFE/SPIRE extension available in upstream",
            "OPA admission policies do not check TLS algorithm — PQC compliance unenforced",
        ],
        "next_steps": [
            "Track SPIFFE/SPIRE upstream for PQC SVID support",
            "Test Istio with hybrid ML-KEM + ECDSA cipher in lab",
            "Add OPA admission policy rule to flag non-PQC mTLS ciphers",
            "Coordinate with L25 Zero Trust on SPIRE upgrade timeline",
        ],
        "effort_to_next_level": "6 months",
        "blocking_dependencies": ["L06 (PKI)", "L25 (Zero Trust SPIRE)"],
    },
    {
        "layer_id": "L20",
        "layer_name": "IoT Security",
        "current_level": 0,
        "justification": (
            "127 IoT devices deployed. DTLS 1.2 with ECC. Devices have 10-year "
            "lifecycle — HNDL risk is CRITICAL (device comms today decrypted by "
            "2034 CRQC). No OTA PQC firmware update capability. Provisioning uses "
            "ECDSA certificates."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  2,
            "migration_plan":   1,
            "tooling":          0,
            "monitoring":       1,
            "compliance":       0,
        },
        "gaps": [
            "127 IoT devices: DTLS 1.2 ECC — 10-year lifecycle creates extreme HNDL window",
            "No OTA PQC update mechanism — devices cannot receive algorithm upgrade",
            "Provisioning certificates ECDSA P-256 with no PQC migration path",
            "Constrained devices (ARM Cortex-M4) may lack compute for ML-KEM — not assessed",
            "No firmware crypto inventory across device fleet",
        ],
        "next_steps": [
            "Conduct IoT device crypto inventory (algorithm, key size, OTA capability)",
            "Benchmark ML-KEM-512 on representative IoT hardware (Cortex-M4)",
            "Identify devices with no OTA capability — plan physical replacement schedule",
            "Evaluate DTLS 1.3 PQC draft (draft-ietf-tls-dtls-pqc) applicability",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": [],
    },
    {
        "layer_id": "L21",
        "layer_name": "Mobile Security",
        "current_level": 1,
        "justification": (
            "Mobile apps use certificate pinning (ECDSA P-256). FIDO2 ECDSA "
            "credentials in authenticator. Certificate pinning blocks cert "
            "migration without app update. App update lifecycle is 3-6 months."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  2,
            "migration_plan":   1,
            "tooling":          1,
            "monitoring":       1,
            "compliance":       1,
        },
        "gaps": [
            "Certificate pinning blocks PQC cert migration — requires coordinated app release",
            "FIDO2 ECDSA P-256 credentials: no PQC FIDO2 credential type standardised",
            "App store release cycle (3-6 months) creates migration planning constraint",
            "FIDO Alliance PQC FIDO2 spec not yet published",
        ],
        "next_steps": [
            "Plan coordinated app update for cert-pin migration (next major release)",
            "Track FIDO Alliance PQC FIDO2 working group",
            "Implement FIDO2 backup credentials alongside ECDSA during transition",
            "Remove hard-coded cert pins; move to dynamic trust-store management",
        ],
        "effort_to_next_level": "6 months",
        "blocking_dependencies": ["L06 (PKI for new certs)", "App release schedule"],
    },
    {
        "layer_id": "L22",
        "layer_name": "Firmware / Secure Boot",
        "current_level": 0,
        "justification": (
            "UEFI Secure Boot uses RSA-2048 signing. TPM 2.0 present — TPM 3.0 "
            "not available. Firmware signing key stored in offline HSM (RSA). "
            "No PQC firmware signing tool available from OEMs. HNDL risk on "
            "long-lived firmware archives."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  3,
            "migration_plan":   1,
            "tooling":          0,
            "monitoring":       2,
            "compliance":       0,
        },
        "gaps": [
            "UEFI Secure Boot RSA-2048 signature — forged firmware possible post-CRQC",
            "TPM 3.0 not available from server OEMs; TPM 2.0 lacks PQC support",
            "Firmware signing toolchain has no ML-DSA signing option",
            "OEM firmware update packages not PQC-signed — supply chain risk",
            "Long-term firmware archives (ITAR-retention) at HNDL risk",
        ],
        "next_steps": [
            "Inventory all firmware signing keys and their algorithms",
            "Engage OEM vendors (Dell, HP, Lenovo) on TPM 3.0 / PQC Secure Boot roadmap",
            "Evaluate NIST NCCoE project on PQC firmware signing",
            "Assess sbctl / shim build for experimental ML-DSA Secure Boot signing",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": ["OEM hardware roadmap"],
    },
    {
        "layer_id": "L23",
        "layer_name": "DevSecOps",
        "current_level": 1,
        "justification": (
            "GPG commit signing (RSA) in GitHub Actions. Vault CI integration "
            "uses RSA-wrapped secrets. SAST/DAST pipelines running but no PQC "
            "crypto scanner. SBOMs generated but no CBOM extension."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  2,
            "migration_plan":   2,
            "tooling":          2,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "GPG RSA commit signing in CI pipeline — all CI artifacts quantum-forgeable",
            "Vault CI secrets wrapped with RSA-OAEP — same HNDL risk as L14",
            "No PQC crypto scanner in SAST pipeline (crqc-scanner or similar)",
            "SBOM generated but no CBOM extension (crypto component inventory missing)",
        ],
        "next_steps": [
            "Add cbomkit or similar CBOM generation step to CI pipeline",
            "Switch CI GPG signing to Ed25519 (interim step)",
            "Integrate Vault PQC plugin for CI secret wrapping when available",
            "Add PQC compliance gate to deployment pipeline",
        ],
        "effort_to_next_level": "1 month",
        "blocking_dependencies": ["L14 (Vault KMS)"],
    },
    {
        "layer_id": "L24",
        "layer_name": "SIEM / Logging",
        "current_level": 2,
        "justification": (
            "Elasticsearch SIEM deployed. Log shipping via Beats with TLS. "
            "Elastic agent auth uses ECDSA certs. Crypto algorithm telemetry "
            "partially configured (TLS version monitored, cipher not). "
            "SIEM is monitoring platform — lower urgency than data-bearing layers."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  2,
            "migration_plan":   2,
            "tooling":          2,
            "monitoring":       4,
            "compliance":       2,
        },
        "gaps": [
            "Elastic agent auth ECDSA certs — not urgent but needs roadmap",
            "Log shipping TLS uses RSA cert (Beats ➜ Logstash)",
            "SIEM does not alert on RSA/ECDSA cipher suite negotiations",
            "No crypto-algorithm KPI dashboard in Kibana",
        ],
        "next_steps": [
            "Add TLS cipher-suite field to Beats log shipping config",
            "Build Kibana dashboard for crypto algorithm telemetry",
            "Replace Beats ECDSA agent cert with hybrid cert when L06 PKI matures",
            "Create SIEM alert rule: flag any RSA handshake after PQC migration date",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L06 (PKI certs)"],
    },
    {
        "layer_id": "L25",
        "layer_name": "Zero Trust",
        "current_level": 1,
        "justification": (
            "Zero Trust architecture implemented with SPIRE + Pomerium + OPA. "
            "SPIRE issues ECDSA SVIDs (89 workloads). Pomerium OIDC RS256. "
            "Zero Trust policy engine (OPA) does not enforce PQC algorithm."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       3,
            "compliance":       1,
        },
        "gaps": [
            "SPIRE ECDSA SVIDs on 89 workloads — all mutual auth breakable",
            "Pomerium OIDC RS256 — identity provider tokens forgeable",
            "OPA policies do not validate PQC algorithm compliance",
            "Zero Trust crypto requirements not documented in policy",
        ],
        "next_steps": [
            "Track SPIFFE/SPIRE upstream PQC SVID support",
            "Update OPA Rego policies to include crypto algorithm checks",
            "Coordinate Pomerium OIDC migration with L15 IAM workstream",
            "Document Zero Trust PQC crypto requirements in architecture decision record",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L15 (IAM)", "L19 (service mesh SPIRE)"],
    },
    {
        "layer_id": "L26",
        "layer_name": "Key Management / KMS",
        "current_level": 2,
        "justification": (
            "Vault KMS manages 1,247 key wrappings (RSA-OAEP). SOPS uses "
            "RSA-4096 for secrets management. Key rotation policy exists. "
            "Migration plan approved: Vault Transit ➜ ML-KEM wrapping. "
            "Tool not yet GA."
        ),
        "sub_scores": {
            "crypto_inventory": 4,
            "risk_assessment":  4,
            "migration_plan":   3,
            "tooling":          2,
            "monitoring":       3,
            "compliance":       2,
        },
        "gaps": [
            "Vault RSA-OAEP 1,247 key wrappings — all DEKs recoverable post-CRQC",
            "SOPS RSA-4096 encryption for secrets management — same risk class",
            "ML-KEM key wrapping not deployed (plugin in preview, not GA)",
            "Key rotation under ML-KEM not tested; rotation may break downstream",
        ],
        "next_steps": [
            "Run Vault Transit ML-KEM pilot on non-production key set",
            "Migrate SOPS to age (X25519 interim) then to ML-KEM when stable",
            "Document key-wrapping algorithm for each KMS entry in CBOM",
            "Test key rotation automation under ML-KEM wrapping",
        ],
        "effort_to_next_level": "6 months",
        "blocking_dependencies": ["L14 (HSM hardware)"],
    },
    {
        "layer_id": "L27",
        "layer_name": "Compliance",
        "current_level": 2,
        "justification": (
            "FIPS 140-2 validated modules in use. SOC 2 Type II certified. "
            "PCI-DSS v4 gap analysis in progress. No formal CNSA 2.0 assessment "
            "completed. FIPS 140-3 transition not started. Compliance team aware "
            "of quantum risk."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   3,
            "tooling":          3,
            "monitoring":       3,
            "compliance":       2,
        },
        "gaps": [
            "FIPS 140-2 only — FIPS 140-3 transition plan not started",
            "No formal CNSA 2.0 (NSA) compliance assessment completed",
            "PCI-DSS v4 PQC requirements gap analysis not finished",
            "SOC 2 does not cover quantum cryptography controls yet",
        ],
        "next_steps": [
            "Commission formal CNSA 2.0 gap assessment with QSA",
            "Start FIPS 140-3 transition planning with CMVP-validated module vendor",
            "Complete PCI-DSS v4 PQC gap analysis",
            "Add quantum risk to SOC 2 risk register",
        ],
        "effort_to_next_level": "6 months",
        "blocking_dependencies": ["L14 (FIPS 140-3 HSM procurement)"],
    },
    {
        "layer_id": "L28",
        "layer_name": "Audit / Non-Repudiation",
        "current_level": 1,
        "justification": (
            "RFC 3161 timestamps using RSA-2048 TSA. 30-year archival requirement "
            "for financial records. SLH-DSA (FIPS 205) identified as ideal for "
            "long-lived signatures but not deployed. Audit log integrity uses "
            "HMAC-SHA256 (safe)."
        ),
        "sub_scores": {
            "crypto_inventory": 3,
            "risk_assessment":  3,
            "migration_plan":   2,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "RFC 3161 timestamps RSA-2048 — 30-year archival signatures at retroactive risk",
            "SLH-DSA (FIPS 205) not deployed for long-lived archival signing",
            "TSA (timestamp authority) vendor has no PQC roadmap documented",
            "Legal / compliance review of PQC timestamp validity not completed",
        ],
        "next_steps": [
            "Identify and contact TSA vendor about SLH-DSA / PQC timestamp support",
            "Evaluate self-hosted RFC 3161 TSA with SLH-DSA signing capability",
            "Re-timestamp highest-risk archival documents with hybrid signature",
            "Legal review: admissibility of PQC-signed archival records",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L06 (PKI)"],
    },
    {
        "layer_id": "L29",
        "layer_name": "AI/ML Security",
        "current_level": 1,
        "justification": (
            "cosign ECDSA P-256 used for ML model signing in CI. MLflow REST API "
            "uses RS256 JWT tokens. Model artifact integrity not verified at "
            "inference time. No ML-DSA model signing deployed. AI security "
            "awareness of quantum risk is low."
        ),
        "sub_scores": {
            "crypto_inventory": 2,
            "risk_assessment":  2,
            "migration_plan":   1,
            "tooling":          1,
            "monitoring":       2,
            "compliance":       1,
        },
        "gaps": [
            "cosign ECDSA model signing — trained model artifacts forgeable post-CRQC",
            "MLflow RS256 API tokens — model registry access tokens quantum-forgeable",
            "No ML-DSA model signing configured in any pipeline",
            "Model integrity not verified at inference time (only at upload)",
        ],
        "next_steps": [
            "Track cosign / notation ML-DSA support for model signing",
            "Migrate MLflow API to ML-DSA JWT tokens when available",
            "Implement runtime model hash verification at inference",
            "Add AI/ML crypto inventory to CBOM pipeline",
        ],
        "effort_to_next_level": "3 months",
        "blocking_dependencies": ["L12 (code signing toolchain)"],
    },
]


# ─── MaturityModel class ──────────────────────────────────────────────────────

class MaturityModel:
    """Quantum Security Maturity Model — 29-layer assessment."""

    LEVEL_LABELS = {
        0: "L0 Unaware",
        1: "L1 Aware",
        2: "L2 Assessed",
        3: "L3 Migrating",
        4: "L4 Migrated",
        5: "L5 Optimized",
    }

    # Rough weights by security impact
    LAYER_WEIGHTS = {
        "L04": 1.5,  # TLS — high exposure
        "L06": 1.5,  # PKI — root of trust
        "L14": 1.4,  # HSM/KMS — key material
        "L26": 1.4,  # KMS
        "L08": 1.2,  # JWT/Auth
        "L15": 1.2,  # IAM
        "L03": 1.2,  # IPsec
        "L18": 1.3,  # Blockchain — financial exposure
        "L20": 1.2,  # IoT — lifecycle risk
        "L22": 1.2,  # Firmware
    }

    def __init__(self) -> None:
        self._layers: dict[str, LayerMaturity] = {}
        for raw in _RAW_LAYERS:
            lm = LayerMaturity(**raw)
            self._layers[lm.layer_id] = lm

    # ── Public API ────────────────────────────────────────────────────────────

    def get_layer_maturity(self, layer_id: str) -> dict[str, Any]:
        """Return full maturity dict for one layer."""
        lm = self._layers.get(layer_id.upper())
        if lm is None:
            raise KeyError(f"Layer '{layer_id}' not found. Valid IDs: {list(self._layers)}")
        d = asdict(lm)
        d["level_badge"] = lm.level_badge
        d["average_score"] = lm.average_score
        return d

    def get_all_layers(self) -> list[dict[str, Any]]:
        """Return list of all 29 layers with their maturity data."""
        return [self.get_layer_maturity(lid) for lid in sorted(self._layers)]

    def get_overall_score(self) -> float:
        """Return weighted average maturity score 0-5."""
        total_weight = 0.0
        weighted_sum = 0.0
        for lid, lm in self._layers.items():
            w = self.LAYER_WEIGHTS.get(lid, 1.0)
            weighted_sum += lm.current_level * w
            total_weight += w
        return round(weighted_sum / total_weight, 2) if total_weight else 0.0

    def get_by_level(self, level: int) -> list[dict[str, Any]]:
        """Return layers at a given maturity level (0-5)."""
        return [
            self.get_layer_maturity(lid)
            for lid, lm in sorted(self._layers.items())
            if lm.current_level == level
        ]

    def get_radar_data(self, layer_id: str) -> dict[str, Any]:
        """Return 6-dimension radar chart data for a layer."""
        lm = self._layers.get(layer_id.upper())
        if lm is None:
            raise KeyError(f"Layer '{layer_id}' not found")
        dims = ["crypto_inventory", "risk_assessment", "migration_plan",
                "tooling", "monitoring", "compliance"]
        return {
            "layer_id": lm.layer_id,
            "layer_name": lm.layer_name,
            "current_level": lm.current_level,
            "dimensions": {d: lm.sub_scores.get(d, 0) for d in dims},
        }

    def get_migration_roadmap(self) -> dict[str, list[dict[str, Any]]]:
        """Return P0/P1/P2/P3 prioritised migration list."""
        roadmap: dict[str, list[dict[str, Any]]] = {
            "P0_immediate": [],   # Level 0 — act now
            "P1_3months":   [],   # Level 1, high criticality
            "P2_6months":   [],   # Level 1-2, medium criticality
            "P3_12months":  [],   # Level 2-3, lower urgency
        }

        _p0_ids = {"L11", "L18", "L20", "L22"}
        _p1_ids = {"L04", "L06", "L08", "L03", "L15", "L14", "L13"}
        _p2_ids = {"L09", "L05", "L02", "L16", "L19", "L25", "L26", "L27", "L28", "L29"}

        for lid, lm in sorted(self._layers.items()):
            entry = {
                "layer_id": lid,
                "layer_name": lm.layer_name,
                "current_level": lm.current_level,
                "effort": lm.effort_to_next_level,
                "next_steps": lm.next_steps[:2],
            }
            if lid in _p0_ids:
                roadmap["P0_immediate"].append(entry)
            elif lid in _p1_ids:
                roadmap["P1_3months"].append(entry)
            elif lid in _p2_ids:
                roadmap["P2_6months"].append(entry)
            else:
                roadmap["P3_12months"].append(entry)

        return roadmap

    def generate_report(self) -> str:
        """Return formatted executive maturity report."""
        lines: list[str] = []
        lines.append("=" * 76)
        lines.append(" QUANTUM SECURITY MATURITY MODEL (QSMM) — EXECUTIVE REPORT")
        lines.append("=" * 76)
        lines.append(f" Assessment Date : 2026-10-01")
        lines.append(f" Total Layers    : 29")
        overall = self.get_overall_score()
        lines.append(f" Overall Score   : {overall:.2f} / 5.00")
        label = self.LEVEL_LABELS.get(round(overall), "UNKNOWN")
        lines.append(f" Maturity Level  : {label}")
        lines.append(f" CNSA 2.0 Target : Level 4 by 2027")
        lines.append("")

        # Distribution
        lines.append("-" * 76)
        lines.append(" LEVEL DISTRIBUTION")
        lines.append("-" * 76)
        for lvl in range(6):
            layers_at = self.get_by_level(lvl)
            bar = "█" * len(layers_at)
            lines.append(f"  {self.LEVEL_LABELS[lvl]:<18} {bar:<20} {len(layers_at):>2} layers")
        lines.append("")

        # Summary table
        lines.append("-" * 76)
        lines.append(f" {'ID':<5} {'Layer Name':<30} {'Level':<12} {'Score':>5}  {'Badge'}")
        lines.append("-" * 76)
        for lm_dict in self.get_all_layers():
            lid   = lm_dict["layer_id"]
            name  = lm_dict["layer_name"][:28]
            lvl   = lm_dict["current_level"]
            score = lm_dict["average_score"]
            badge = lm_dict["level_badge"]
            lines.append(f"  {lid:<5} {name:<30} {lvl:<12} {score:>5.2f}  {badge}")
        lines.append("")

        # P0 layers
        lines.append("-" * 76)
        lines.append(" P0 — IMMEDIATE ACTION REQUIRED (Level 0)")
        lines.append("-" * 76)
        for entry in self.get_by_level(0):
            lines.append(f"  {entry['layer_id']} {entry['layer_name']}")
            for gap in entry["gaps"][:2]:
                lines.append(f"     ✗ {gap}")
        lines.append("")

        # Quick wins
        lines.append("-" * 76)
        lines.append(" TOP 5 QUICK WINS (Level 1 → Level 2, lowest effort)")
        lines.append("-" * 76)
        _effort_order = {"1 month": 0, "3 months": 1, "6 months": 2, "1 year": 3}
        l1_layers = sorted(
            self.get_by_level(1),
            key=lambda x: _effort_order.get(x["effort_to_next_level"], 9)
        )
        for entry in l1_layers[:5]:
            lines.append(
                f"  {entry['layer_id']} {entry['layer_name']:<30} "
                f"Effort: {entry['effort_to_next_level']}"
            )
            lines.append(f"     → {entry['next_steps'][0]}")
        lines.append("")

        # Radar for top 3 critical
        lines.append("-" * 76)
        lines.append(" RADAR DATA — TOP 3 CRITICAL LAYERS (L04, L06, L08)")
        lines.append("-" * 76)
        for lid in ["L04", "L06", "L08"]:
            rd = self.get_radar_data(lid)
            lines.append(f"\n  {rd['layer_id']} {rd['layer_name']} — Level {rd['current_level']}")
            for dim, score in rd["dimensions"].items():
                bar = "▓" * score + "░" * (5 - score)
                lines.append(f"    {dim:<20} {bar}  {score}/5")

        lines.append("")
        lines.append("=" * 76)
        return "\n".join(lines)


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    model = MaturityModel()

    print("\n" + model.generate_report())

    # 1. Summary table (already in report — reprint compact for CI)
    print("\n── ALL 29 LAYERS COMPACT TABLE ──")
    header = f"{'ID':<5} {'Name':<32} {'Lvl':>3}  {'Score':>5}  {'Badge'}"
    print(header)
    print("-" * len(header))
    for lm in model.get_all_layers():
        print(
            f"{lm['layer_id']:<5} {lm['layer_name'][:30]:<32} "
            f"{lm['current_level']:>3}  {lm['average_score']:>5.2f}  {lm['level_badge']}"
        )

    # 2. Distribution
    print("\n── LEVEL DISTRIBUTION ──")
    for lvl in range(6):
        count = len(model.get_by_level(lvl))
        print(f"  Level {lvl}: {count:>2} layers")

    overall = model.get_overall_score()
    print(f"\n  Overall weighted score: {overall:.2f} / 5.00")

    # 3. P0 priorities
    print("\n── P0 PRIORITIES (Level 0 — Immediate Action) ──")
    for entry in model.get_by_level(0):
        print(f"  {entry['layer_id']} {entry['layer_name']}")
        print(f"     Critical gap: {entry['gaps'][0]}")

    # 4. Top 5 quick wins
    _effort_order = {"1 month": 0, "3 months": 1, "6 months": 2, "1 year": 3}
    l1_sorted = sorted(
        model.get_by_level(1),
        key=lambda x: _effort_order.get(x["effort_to_next_level"], 9),
    )
    print("\n── TOP 5 QUICK WINS (Level 1, lowest effort) ──")
    for entry in l1_sorted[:5]:
        print(
            f"  {entry['layer_id']} {entry['layer_name']:<30}  "
            f"[{entry['effort_to_next_level']}]  → {entry['next_steps'][0]}"
        )

    # 5. Radar data for top 3 critical layers
    print("\n── RADAR DATA (L04 TLS, L06 PKI, L08 JWT) ──")
    for lid in ["L04", "L06", "L08"]:
        rd = model.get_radar_data(lid)
        print(f"\n  {rd['layer_id']} {rd['layer_name']} (Level {rd['current_level']})")
        print(f"  {json.dumps(rd['dimensions'], indent=4)}")


if __name__ == "__main__":
    main()
