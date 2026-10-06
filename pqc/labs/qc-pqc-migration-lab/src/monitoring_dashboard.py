"""
PQC Migration Monitoring Dashboard
Tracks 29 architecture layers through their quantum-safe migration.

Compliance frameworks tracked:
  - FIPS 140-3 (cryptographic module validation)
  - NIST SP 800-208 (recommendation for stateful hash-based signature schemes)
  - CNSA 2.0 (Commercial National Security Algorithm Suite 2.0)
  - NIST SP 800-131Ar3 (transitioning use of cryptographic algorithms)
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta


# ─── Enumerations ────────────────────────────────────────────────────────────

class MigrationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    TESTING     = "TESTING"
    COMPLETED   = "COMPLETED"


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


# ─── Layer record ─────────────────────────────────────────────────────────────

@dataclass
class LayerMigrationRecord:
    layer_id: int
    layer_name: str
    old_algorithm: str
    new_algorithm: str
    risk_level: RiskLevel
    migration_status: MigrationStatus
    migration_start_date: Optional[str]        # ISO date or None
    target_completion: str                      # ISO date
    test_coverage_percent: int                  # 0–100
    rollback_plan: str
    monitoring_metrics: List[str]
    notes: str = ""


# ─── Layer definitions (29 layers) ────────────────────────────────────────────

def _build_layers() -> List[LayerMigrationRecord]:
    today = datetime(2025, 1, 1)

    def iso(offset_months: int, base=today) -> str:
        import calendar
        y = base.year + (base.month + offset_months - 1) // 12
        m = (base.month + offset_months - 1) % 12 + 1
        d = min(base.day, calendar.monthrange(y, m)[1])
        return datetime(y, m, d).strftime("%Y-%m-%d")

    def start(offset_months: int) -> Optional[str]:
        if offset_months < 0:
            return None
        return iso(offset_months)

    layers = [
        # ── Completed ──────────────────────────────────────────────────
        LayerMigrationRecord(
            layer_id=1, layer_name="Hash Functions",
            old_algorithm="SHA-256", new_algorithm="SHA-384 / SHA3-256",
            risk_level=RiskLevel.MEDIUM,
            migration_status=MigrationStatus.COMPLETED,
            migration_start_date=iso(-12), target_completion=iso(-6),
            test_coverage_percent=100,
            rollback_plan="Revert hash config in crypto provider; no key material at risk",
            monitoring_metrics=["hash_algo_distribution", "deprecated_sha1_usage",
                                 "sha256_usage_trend"],
        ),
        LayerMigrationRecord(
            layer_id=2, layer_name="Symmetric Encryption (DB at-rest)",
            old_algorithm="AES-128-CBC", new_algorithm="AES-256-GCM",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.COMPLETED,
            migration_start_date=iso(-10), target_completion=iso(-4),
            test_coverage_percent=98,
            rollback_plan="Dual-key decryption during rotation; 30-day rollback window",
            monitoring_metrics=["reencryption_progress_pct", "db_latency_p99",
                                 "aes128_tablespace_count", "key_rotation_events"],
        ),
        LayerMigrationRecord(
            layer_id=3, layer_name="TLS Internal Services",
            old_algorithm="ECDSA-P256 + ECDHE", new_algorithm="ML-DSA-65 + X25519+ML-KEM-768",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.COMPLETED,
            migration_start_date=iso(-8), target_completion=iso(-2),
            test_coverage_percent=96,
            rollback_plan="Classical TLS 1.3 cipher suites remain available for 90 days",
            monitoring_metrics=["hybrid_kex_adoption_pct", "classical_fallback_count",
                                 "cert_expiry_alerts", "handshake_latency_p99"],
        ),
        LayerMigrationRecord(
            layer_id=4, layer_name="HMAC / Message Authentication",
            old_algorithm="HMAC-SHA1 / HMAC-MD5", new_algorithm="HMAC-SHA256 / HMAC-SHA384",
            risk_level=RiskLevel.MEDIUM,
            migration_status=MigrationStatus.COMPLETED,
            migration_start_date=iso(-14), target_completion=iso(-8),
            test_coverage_percent=100,
            rollback_plan="N/A — MAC change is configuration-only; no stored ciphertext",
            monitoring_metrics=["hmac_sha1_usage_count", "hmac_sha256_adoption_pct"],
        ),
        LayerMigrationRecord(
            layer_id=5, layer_name="Key Derivation (KDF)",
            old_algorithm="PBKDF2-SHA1 / bcrypt", new_algorithm="Argon2id / HKDF-SHA384",
            risk_level=RiskLevel.MEDIUM,
            migration_status=MigrationStatus.COMPLETED,
            migration_start_date=iso(-9), target_completion=iso(-3),
            test_coverage_percent=94,
            rollback_plan="Legacy KDF path retained for existing password hashes during migration",
            monitoring_metrics=["argon2id_adoption_pct", "legacy_kdf_active_sessions"],
        ),
        # ── Testing ────────────────────────────────────────────────────
        LayerMigrationRecord(
            layer_id=6, layer_name="JWT / OAuth Token Signing",
            old_algorithm="RS256 (RSA-2048)", new_algorithm="ML-DSA-65",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.TESTING,
            migration_start_date=iso(-3), target_completion=iso(3),
            test_coverage_percent=72,
            rollback_plan="Dual-token issuer active; RS256 JWKS remains live until P0 achieved",
            monitoring_metrics=["mldsa65_token_issuance_pct", "rs256_fallback_count",
                                 "token_size_distribution", "verify_latency_p99"],
        ),
        LayerMigrationRecord(
            layer_id=7, layer_name="TLS External (Public-Facing)",
            old_algorithm="RSA-2048 cert + ECDHE", new_algorithm="ML-DSA-65 cert + X25519+ML-KEM-768",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.TESTING,
            migration_start_date=iso(-2), target_completion=iso(4),
            test_coverage_percent=65,
            rollback_plan="Classical TLS 1.3 profile maintained; CDN classical fallback active",
            monitoring_metrics=["hybrid_group_negotiation_pct", "browser_fallback_count",
                                 "rsa_cert_expiry", "kem_ct_size_bytes"],
        ),
        LayerMigrationRecord(
            layer_id=8, layer_name="SSH Host Keys",
            old_algorithm="Ed25519", new_algorithm="ML-DSA-65",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.TESTING,
            migration_start_date=iso(-1), target_completion=iso(3),
            test_coverage_percent=58,
            rollback_plan="Dual host keys advertised; Ed25519 fallback for < OpenSSH 9.0 clients",
            monitoring_metrics=["mldsa65_host_key_adoption", "known_hosts_update_pct",
                                 "openssh_version_distribution"],
        ),
        LayerMigrationRecord(
            layer_id=9, layer_name="PKI Root CA",
            old_algorithm="RSA-4096", new_algorithm="ML-DSA-87",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.TESTING,
            migration_start_date=iso(-4), target_completion=iso(6),
            test_coverage_percent=45,
            rollback_plan="Legacy root CA remains in trust store for 2 years post-migration",
            monitoring_metrics=["new_root_distribution_pct", "cert_chain_validation_errors",
                                 "crl_issuance_latency", "ocsp_response_time"],
        ),
        LayerMigrationRecord(
            layer_id=10, layer_name="PKI Intermediate CA",
            old_algorithm="RSA-2048", new_algorithm="ML-DSA-65",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.TESTING,
            migration_start_date=iso(-3), target_completion=iso(5),
            test_coverage_percent=50,
            rollback_plan="Classical intermediate remains active; PQC intermediate runs in parallel",
            monitoring_metrics=["cert_issuance_by_ca", "intermediate_ocsp_latency",
                                 "cert_path_length"],
        ),
        # ── In Progress ────────────────────────────────────────────────
        LayerMigrationRecord(
            layer_id=11, layer_name="VPN IKEv2 Key Exchange",
            old_algorithm="DH-2048 + RSA", new_algorithm="ML-KEM-768 + ML-DSA-65",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.IN_PROGRESS,
            migration_start_date=iso(0), target_completion=iso(9),
            test_coverage_percent=30,
            rollback_plan="IKEv2 classical proposal maintained as fallback; manual revert SLA 4h",
            monitoring_metrics=["ike_sa_pqc_negotiated_pct", "vpn_client_version_dist",
                                 "ike_sa_setup_time_ms", "rekeyInterval"],
        ),
        LayerMigrationRecord(
            layer_id=12, layer_name="Code Signing (CI/CD)",
            old_algorithm="RSA-4096", new_algorithm="ML-DSA-87",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.IN_PROGRESS,
            migration_start_date=iso(1), target_completion=iso(12),
            test_coverage_percent=22,
            rollback_plan="Dual-sign artifacts for 12-month overlap; legacy sig verified first",
            monitoring_metrics=["dual_sign_artifact_pct", "deploy_verify_failure_rate",
                                 "signing_cert_expiry", "ci_build_sign_latency_ms"],
        ),
        LayerMigrationRecord(
            layer_id=13, layer_name="Disk Encryption (LUKS)",
            old_algorithm="AES-128-XTS", new_algorithm="AES-256-XTS",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.IN_PROGRESS,
            migration_start_date=iso(0), target_completion=iso(6),
            test_coverage_percent=18,
            rollback_plan="Full disk re-encryption reversible; backup decrypt keys held in HSM",
            monitoring_metrics=["luks_rekey_progress_pct", "disk_throughput_delta",
                                 "aes128_volume_count"],
        ),
        LayerMigrationRecord(
            layer_id=14, layer_name="API Gateway mTLS",
            old_algorithm="ECDSA-P256 client certs", new_algorithm="ML-DSA-65 client certs",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.IN_PROGRESS,
            migration_start_date=iso(-1), target_completion=iso(5),
            test_coverage_percent=35,
            rollback_plan="Accept both ECDSA-P256 and ML-DSA-65 client certs during transition",
            monitoring_metrics=["pqc_mtls_cert_pct", "mtls_handshake_failure_rate",
                                 "client_cert_algorithm_histogram"],
        ),
        LayerMigrationRecord(
            layer_id=15, layer_name="S3 / Object Storage Encryption",
            old_algorithm="AES-128-CBC", new_algorithm="AES-256-GCM",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.IN_PROGRESS,
            migration_start_date=iso(0), target_completion=iso(4),
            test_coverage_percent=40,
            rollback_plan="Object-level re-encryption; old key retained in KMS for 60 days",
            monitoring_metrics=["object_reencrypt_pct", "s3_put_latency_p99",
                                 "kms_call_rate"],
        ),
        LayerMigrationRecord(
            layer_id=16, layer_name="Email Encryption (S/MIME)",
            old_algorithm="RSA-2048 + AES-128", new_algorithm="ML-KEM-768 + AES-256",
            risk_level=RiskLevel.MEDIUM,
            migration_status=MigrationStatus.IN_PROGRESS,
            migration_start_date=iso(2), target_completion=iso(10),
            test_coverage_percent=15,
            rollback_plan="Dual-cert distribution; legacy cert active for external parties",
            monitoring_metrics=["pqc_smime_cert_adoption", "email_encryption_failure_rate",
                                 "cert_revocation_events"],
        ),
        # ── Not Started ────────────────────────────────────────────────
        LayerMigrationRecord(
            layer_id=17, layer_name="Firmware Signing",
            old_algorithm="RSA-2048", new_algorithm="ML-DSA-65 + SLH-DSA-128s",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(18),
            test_coverage_percent=0,
            rollback_plan="Device reflash with classical firmware; requires physical access",
            monitoring_metrics=["firmware_pqc_signed_pct", "device_update_success_rate",
                                 "boot_sig_verify_failures"],
        ),
        LayerMigrationRecord(
            layer_id=18, layer_name="Secure Boot (UEFI)",
            old_algorithm="RSA-2048 (db/dbx keys)", new_algorithm="ML-DSA-65",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(24),
            test_coverage_percent=0,
            rollback_plan="MOK enrollment allows legacy key; requires BIOS vendor support",
            monitoring_metrics=["secure_boot_pqc_key_enrolled_pct", "boot_failure_rate",
                                 "uefi_db_update_events"],
        ),
        LayerMigrationRecord(
            layer_id=19, layer_name="HSM / Key Management",
            old_algorithm="RSA-2048 wrapping keys", new_algorithm="ML-KEM-768",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(15),
            test_coverage_percent=0,
            rollback_plan="Dual HSM partition; classical partition kept warm for 6 months",
            monitoring_metrics=["hsm_pqc_key_count", "key_wrap_latency_ms",
                                 "hsm_firmware_version"],
        ),
        LayerMigrationRecord(
            layer_id=20, layer_name="Smart Card / PIV Credentials",
            old_algorithm="RSA-2048 / ECDSA-P256", new_algorithm="ML-DSA-65",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(20),
            test_coverage_percent=0,
            rollback_plan="Legacy PIV cards remain valid; dual readers during transition",
            monitoring_metrics=["piv_pqc_card_issuance_pct", "auth_failure_rate",
                                 "card_reader_fw_version"],
        ),
        LayerMigrationRecord(
            layer_id=21, layer_name="DNS Security (DNSSEC)",
            old_algorithm="ECDSA-P256 (Algorithm 13)", new_algorithm="ML-DSA-65 (Algorithm TBD)",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(24),
            test_coverage_percent=0,
            rollback_plan="Dual KSK/ZSK signing; classic signatures remain for unsupported resolvers",
            monitoring_metrics=["dnssec_validation_success_rate", "zone_signing_latency",
                                 "resolver_pqc_support_pct"],
        ),
        LayerMigrationRecord(
            layer_id=22, layer_name="Container Image Signing",
            old_algorithm="ECDSA-P256 (Cosign/Notary)", new_algorithm="ML-DSA-65",
            risk_level=RiskLevel.MEDIUM,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(12),
            test_coverage_percent=0,
            rollback_plan="Sigstore rekor log immutable; keep ECDSA key active in Fulcio for 1 year",
            monitoring_metrics=["pqc_signed_image_pct", "image_verify_failure_rate",
                                 "cosign_verify_latency_ms"],
        ),
        LayerMigrationRecord(
            layer_id=23, layer_name="Backup Encryption",
            old_algorithm="AES-128 + RSA-2048 wrap", new_algorithm="AES-256 + ML-KEM-768 wrap",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(9),
            test_coverage_percent=0,
            rollback_plan="Old backup keys retained in escrow; decrypt-then-re-encrypt on restore",
            monitoring_metrics=["backup_reencrypt_progress_pct", "restore_test_success",
                                 "backup_job_duration_delta"],
        ),
        LayerMigrationRecord(
            layer_id=24, layer_name="Service Mesh mTLS (Istio/Envoy)",
            old_algorithm="ECDSA-P256", new_algorithm="ML-DSA-65",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(14),
            test_coverage_percent=0,
            rollback_plan="Istio pilot accepts both ECDSA and ML-DSA CAs; gradual mesh rollout",
            monitoring_metrics=["mesh_pqc_cert_pct", "envoy_handshake_latency_p99",
                                 "mtls_errors_per_service"],
        ),
        LayerMigrationRecord(
            layer_id=25, layer_name="Blockchain / Ledger Keys",
            old_algorithm="ECDSA-secp256k1", new_algorithm="ML-DSA-65 (off-chain) + Dilithium on-chain",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(30),
            test_coverage_percent=0,
            rollback_plan="Hard fork required for on-chain key type change; long planning horizon",
            monitoring_metrics=["pqc_wallet_key_pct", "transaction_verify_time_ms",
                                 "chain_upgrade_block_height"],
        ),
        LayerMigrationRecord(
            layer_id=26, layer_name="Kerberos (Active Directory)",
            old_algorithm="AES-256 (symmetric) + RSA-2048 PKINIT", new_algorithm="AES-256 + ML-DSA-65 PKINIT",
            risk_level=RiskLevel.HIGH,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(18),
            test_coverage_percent=0,
            rollback_plan="Classic PKINIT DC policy retained; PQC PKINIT opt-in per OU",
            monitoring_metrics=["pkinit_pqc_auth_pct", "kerberos_preauth_failures",
                                 "dc_upgrade_pct"],
        ),
        LayerMigrationRecord(
            layer_id=27, layer_name="Wireless Security (WPA3-Enterprise)",
            old_algorithm="ECDSA-P256 (EAP-TLS)", new_algorithm="ML-DSA-65 (EAP-TLS)",
            risk_level=RiskLevel.MEDIUM,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(21),
            test_coverage_percent=0,
            rollback_plan="AP vendor firmware PQC support required; phased AP replacement plan",
            monitoring_metrics=["eap_tls_pqc_auth_pct", "wifi_auth_failure_rate",
                                 "ap_firmware_version_distribution"],
        ),
        LayerMigrationRecord(
            layer_id=28, layer_name="Zero Trust PAM / Secrets Vault",
            old_algorithm="RSA-2048 wrapping", new_algorithm="ML-KEM-768 wrapping + ML-DSA-65 auth",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(12),
            test_coverage_percent=0,
            rollback_plan="HashiCorp Vault seal key fallback; manual unseal with HSM backup",
            monitoring_metrics=["vault_pqc_seal_active", "secret_access_latency_ms",
                                 "seal_unseal_events", "audit_log_integrity_check"],
        ),
        LayerMigrationRecord(
            layer_id=29, layer_name="Cloud KMS (AWS/GCP/Azure)",
            old_algorithm="RSA-2048 / ECDSA-P256 CMK", new_algorithm="ML-DSA-65 + ML-KEM-768 CMK",
            risk_level=RiskLevel.CRITICAL,
            migration_status=MigrationStatus.NOT_STARTED,
            migration_start_date=None, target_completion=iso(15),
            test_coverage_percent=0,
            rollback_plan="Cloud KMS version key feature; keep v1 keys active for 90-day overlap",
            monitoring_metrics=["pqc_cmk_count", "kms_api_latency_p99",
                                 "key_usage_by_algorithm", "cmk_rotation_events"],
        ),
    ]
    return layers


# ─── Monitoring Dashboard ─────────────────────────────────────────────────────

class MonitoringDashboard:
    """Tracks and reports PQC migration status across 29 architecture layers."""

    _COMPLIANCE_FRAMEWORKS = {
        "FIPS 140-3": {
            "description": "Cryptographic module validation (NIST)",
            "requirement": "All cryptographic modules must use FIPS 140-3 validated algorithms",
            "pqc_ready":   True,
            "reference":   "NIST FIPS 140-3 (2019)",
        },
        "NIST SP 800-208": {
            "description": "Recommendation for stateful hash-based signature schemes",
            "requirement": "LMS / XMSS approved for firmware signing use cases",
            "pqc_ready":   True,
            "reference":   "NIST SP 800-208 (2020)",
        },
        "CNSA 2.0": {
            "description": "Commercial National Security Algorithm Suite 2.0",
            "requirement": "ML-KEM-1024+, ML-DSA-87+, SLH-DSA-256 by 2030 for NSS",
            "pqc_ready":   True,
            "reference":   "NSA CNSA 2.0 (2022)",
        },
        "NIST SP 800-131Ar3": {
            "description": "Transitioning use of cryptographic algorithms and key lengths",
            "requirement": "RSA-2048 / ECDSA-P256 disallowed after 2030",
            "pqc_ready":   True,
            "reference":   "NIST SP 800-131Ar3 (draft 2024)",
        },
    }

    def __init__(self, layers: List[LayerMigrationRecord]):
        self._layers = {l.layer_id: l for l in layers}

    def get_layer_status(self, layer_id: int) -> Optional[LayerMigrationRecord]:
        return self._layers.get(layer_id)

    def get_migration_summary(self) -> Dict[str, Any]:
        layers = list(self._layers.values())
        by_status = {}
        for s in MigrationStatus:
            by_status[s.value] = sum(1 for l in layers if l.migration_status == s)

        by_risk = {}
        for r in RiskLevel:
            by_risk[r.value] = sum(1 for l in layers if l.risk_level == r)

        avg_coverage = sum(l.test_coverage_percent for l in layers) / len(layers)
        completed = [l for l in layers if l.migration_status == MigrationStatus.COMPLETED]
        overall_pct = round(len(completed) / len(layers) * 100, 1)

        critical_not_done = [l for l in layers
                              if l.risk_level == RiskLevel.CRITICAL
                              and l.migration_status != MigrationStatus.COMPLETED]

        return {
            "total_layers":         len(layers),
            "by_status":            by_status,
            "by_risk":              by_risk,
            "avg_test_coverage_pct": round(avg_coverage, 1),
            "overall_progress_pct": overall_pct,
            "critical_not_done":    len(critical_not_done),
            "critical_items":       [l.layer_name for l in critical_not_done],
        }

    def generate_report(self) -> str:
        lines = []
        sep = "=" * 100
        lines.append(sep)
        lines.append(f"  PQC MIGRATION MONITORING DASHBOARD")
        lines.append(f"  Generated : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(sep)

        summary = self.get_migration_summary()
        lines.append(f"\n  OVERALL PROGRESS : {summary['overall_progress_pct']}%")
        lines.append(f"  Total layers     : {summary['total_layers']}")
        for status, count in summary["by_status"].items():
            bar = "█" * count + "░" * (summary["total_layers"] - count)
            lines.append(f"    {status:<15}: {count:>3}  {bar}")

        lines.append(f"\n  RISK BREAKDOWN:")
        for risk, count in summary["by_risk"].items():
            lines.append(f"    {risk:<10}: {count}")

        lines.append(f"\n  Avg test coverage : {summary['avg_test_coverage_pct']}%")
        lines.append(f"  Critical not done : {summary['critical_not_done']} layers")
        if summary["critical_items"]:
            for item in summary["critical_items"]:
                lines.append(f"    [!] {item}")

        lines.append(f"\n{'─'*100}")
        lines.append(f"  {'ID':<4} {'Layer':<35} {'Old Algorithm':<24} {'New Algorithm':<28} "
                     f"{'Status':<15} {'Risk':<10} {'Cov%':>5} {'Target'}")
        lines.append(f"{'─'*100}")

        for layer in sorted(self._layers.values(), key=lambda l: l.layer_id):
            status_icon = {"COMPLETED":"✓","IN_PROGRESS":"►","TESTING":"⊙","NOT_STARTED":"○"}
            icon = status_icon.get(layer.migration_status.value, " ")
            cov_bar = "█" * (layer.test_coverage_percent // 10) + \
                      "░" * (10 - layer.test_coverage_percent // 10)
            lines.append(
                f"  {layer.layer_id:<4} {layer.layer_name:<35} "
                f"{layer.old_algorithm:<24} {layer.new_algorithm:<28} "
                f"{icon} {layer.migration_status.value:<13} {layer.risk_level.value:<10} "
                f"{layer.test_coverage_percent:>4}%  {layer.target_completion}"
            )

        lines.append(f"\n{'─'*100}")
        lines.append(f"  ROLLBACK PLANS (IN_PROGRESS + TESTING layers):")
        for layer in self._layers.values():
            if layer.migration_status in (MigrationStatus.IN_PROGRESS,
                                           MigrationStatus.TESTING):
                lines.append(f"\n  [{layer.layer_id}] {layer.layer_name}")
                lines.append(f"    Rollback: {layer.rollback_plan}")
                lines.append(f"    Metrics : {', '.join(layer.monitoring_metrics[:3])}")

        return "\n".join(lines)

    def check_compliance(self) -> Dict[str, Any]:
        layers = list(self._layers.values())
        completed = [l for l in layers if l.migration_status == MigrationStatus.COMPLETED]
        critical_complete = [l for l in completed if l.risk_level == RiskLevel.CRITICAL]
        all_critical = [l for l in layers if l.risk_level == RiskLevel.CRITICAL]

        results = {}
        for framework, info in self._COMPLIANCE_FRAMEWORKS.items():
            # Simple heuristic: FIPS 140-3 passed if all critical layers completed
            if framework == "FIPS 140-3":
                passed = len(critical_complete) == len(all_critical)
                status = "COMPLIANT" if passed else "NON-COMPLIANT"
                gap = f"{len(all_critical) - len(critical_complete)} critical layers pending"
            elif framework == "CNSA 2.0":
                # CNSA 2.0 requires all CRITICAL + HIGH done
                all_hi = [l for l in layers if l.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)]
                done_hi = [l for l in all_hi if l.migration_status == MigrationStatus.COMPLETED]
                passed = len(done_hi) == len(all_hi)
                status = "IN_PROGRESS"
                gap = f"{len(all_hi) - len(done_hi)} CRITICAL/HIGH layers pending"
            else:
                pct = len(completed) / len(layers)
                status = "COMPLIANT" if pct >= 0.8 else "IN_PROGRESS"
                gap = f"{round(pct*100)}% complete"

            results[framework] = {
                "status":      status,
                "description": info["description"],
                "requirement": info["requirement"],
                "gap":         gap,
                "reference":   info["reference"],
            }

        return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    layers = _build_layers()
    dashboard = MonitoringDashboard(layers)

    # Print the full monitoring report
    print(dashboard.generate_report())

    # Print compliance check
    print("\n" + "=" * 100)
    print("  COMPLIANCE FRAMEWORK STATUS")
    print("=" * 100)
    compliance = dashboard.check_compliance()
    for fw, result in compliance.items():
        icon = "✓" if result["status"] == "COMPLIANT" else \
               "►" if result["status"] == "IN_PROGRESS" else "✗"
        print(f"\n  [{icon}] {fw}  —  {result['status']}")
        print(f"      Requirement : {result['requirement']}")
        print(f"      Gap         : {result['gap']}")
        print(f"      Reference   : {result['reference']}")

    # Example: get single layer status
    print("\n" + "=" * 100)
    print("  SPOT CHECK: Layer 7 (TLS External)")
    print("=" * 100)
    l7 = dashboard.get_layer_status(7)
    if l7:
        print(f"  Layer         : {l7.layer_id} — {l7.layer_name}")
        print(f"  Status        : {l7.migration_status.value}")
        print(f"  Old algorithm : {l7.old_algorithm}")
        print(f"  New algorithm : {l7.new_algorithm}")
        print(f"  Risk          : {l7.risk_level.value}")
        print(f"  Test coverage : {l7.test_coverage_percent}%")
        print(f"  Start date    : {l7.migration_start_date}")
        print(f"  Target done   : {l7.target_completion}")
        print(f"  Rollback      : {l7.rollback_plan}")
        print(f"  Monitoring    :")
        for m in l7.monitoring_metrics:
            print(f"    - {m}")

    summary = dashboard.get_migration_summary()
    print("\n" + "=" * 100)
    print("  SUMMARY")
    print("=" * 100)
    print(f"  Overall migration progress: {summary['overall_progress_pct']}%")
    print(f"  COMPLETED    : {summary['by_status']['COMPLETED']}")
    print(f"  TESTING      : {summary['by_status']['TESTING']}")
    print(f"  IN_PROGRESS  : {summary['by_status']['IN_PROGRESS']}")
    print(f"  NOT_STARTED  : {summary['by_status']['NOT_STARTED']}")


if __name__ == "__main__":
    main()
