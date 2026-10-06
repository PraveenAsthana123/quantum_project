#!/usr/bin/env python3
"""
Generate synthetic security datasets for all 29 security layers.
Layers with real Kaggle data are skipped (L03/L04/L20/L22/L23/L24).
Output: /mnt/deepa/quantum/datasets/security/generated/<layer_id>_<name>.csv
"""
import csv
import json
import random
import math
import pathlib
import datetime
import hashlib
import uuid
import ipaddress

random.seed(42)
ROOT = pathlib.Path(__file__).parent.parent.parent / "datasets" / "security" / "generated"
ROOT.mkdir(parents=True, exist_ok=True)

def rand_ip():
    return str(ipaddress.IPv4Address(random.randint(0x0A000000, 0x0AFFFFFF)))

def rand_mac():
    return ":".join(f"{random.randint(0,255):02x}" for _ in range(6))

def rand_ts(days_back=30):
    base = datetime.datetime(2026, 10, 1, 0, 0, 0)
    delta = datetime.timedelta(seconds=random.randint(0, days_back * 86400))
    return (base - delta).isoformat()

def rand_hash(n=32):
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:n]

def write_csv(name, rows, fieldnames):
    path = ROOT / name
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  ✅  {path.name}  ({len(rows)} rows)")
    return path

# ─────────────────────────────────────────────────────────────────────────────
# L01 Physical — RFID/Badge Access Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l01_physical(n=2000):
    badge_ids = [f"BADGE-{i:04d}" for i in range(1, 150)]
    doors = ["Main Entry", "Server Room A", "Server Room B", "NOC", "Executive Floor",
             "Data Center", "HSM Vault", "Network Closet 3F", "Parking Garage", "Loading Dock"]
    events = ["ACCESS_GRANTED", "ACCESS_DENIED", "TAILGATING_DETECTED", "BADGE_CLONED_ALERT",
              "DOOR_FORCED", "AFTER_HOURS_ACCESS", "RFID_REPLAY_DETECTED", "PIGGYBACKING"]
    weights = [0.55, 0.20, 0.08, 0.04, 0.03, 0.05, 0.03, 0.02]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=weights)[0]
        badge = random.choice(badge_ids)
        door = random.choice(doors)
        is_attack = event in ("BADGE_CLONED_ALERT", "RFID_REPLAY_DETECTED", "DOOR_FORCED", "TAILGATING_DETECTED")
        rows.append({
            "timestamp": rand_ts(),
            "badge_id": badge,
            "door_location": door,
            "event_type": event,
            "signal_strength_dbm": random.randint(-80, -20),
            "read_distance_cm": random.randint(2, 45),
            "frequency_mhz": random.choice([13.56, 125.0, 900.0]),
            "protocol": random.choice(["MIFARE Classic", "HID iCLASS", "DESFire EV2", "EM4100"]),
            "reader_id": f"READER-{random.randint(1,40):03d}",
            "anti_clone_check": random.choice(["PASS", "PASS", "PASS", "FAIL"]) if is_attack else "PASS",
            "pqc_auth_enabled": random.choice([True, False]),
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L01_physical_rfid_access.csv", rows,
              list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L02 MACsec — Ethernet Frame Metadata
# ─────────────────────────────────────────────────────────────────────────────
def gen_l02_macsec(n=3000):
    events = ["FRAME_OK", "REPLAY_WINDOW_VIOLATION", "INTEGRITY_CHECK_FAILED",
              "UNTAGGED_FRAME_DROPPED", "CAM_OVERFLOW", "MACSEC_KEY_EXPIRED", "FRAME_OK"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.60, 0.10, 0.08, 0.09, 0.06, 0.04, 0.03])[0]
        is_attack = event not in ("FRAME_OK",)
        rows.append({
            "timestamp": rand_ts(),
            "src_mac": rand_mac(),
            "dst_mac": rand_mac(),
            "vlan_id": random.randint(1, 4094),
            "frame_size_bytes": random.randint(64, 9000),
            "macsec_tag_present": event != "UNTAGGED_FRAME_DROPPED",
            "sci": f"{rand_hash(12)}:{random.randint(1, 65535)}",
            "packet_number": random.randint(1, 2**32),
            "replay_window_size": random.choice([32, 64, 128]),
            "cipher_suite": random.choice(["GCM-AES-128", "GCM-AES-256", "GCM-AES-XPN-256"]),
            "integrity_check": "PASS" if not is_attack else random.choice(["PASS", "FAIL"]),
            "event_type": event,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L02_macsec_frame_metadata.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L05 Session — JWT / Session Token Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l05_session(n=4000):
    events = ["SESSION_CREATED", "SESSION_VALIDATED", "SESSION_EXPIRED",
              "SESSION_FIXATION_DETECTED", "TOKEN_REPLAY_DETECTED", "CONCURRENT_SESSION_ANOMALY",
              "ENTROPY_TOO_LOW", "SESSION_HIJACKED"]
    rows = []
    for i in range(n):
        event = random.choices(events, weights=[0.30, 0.35, 0.15, 0.07, 0.05, 0.04, 0.02, 0.02])[0]
        is_attack = event in ("SESSION_FIXATION_DETECTED", "TOKEN_REPLAY_DETECTED",
                               "ENTROPY_TOO_LOW", "SESSION_HIJACKED")
        token_entropy = random.uniform(1.5, 2.8) if is_attack else random.uniform(3.5, 8.0)
        rows.append({
            "timestamp": rand_ts(),
            "session_id": rand_hash(32),
            "user_id": f"user_{random.randint(1000, 9999)}",
            "client_ip": rand_ip(),
            "event_type": event,
            "token_entropy_bits": round(token_entropy, 3),
            "token_length_bytes": random.choice([16, 32, 64, 128]),
            "algorithm": random.choice(["HS256", "RS256", "ES256", "none"]) if is_attack else random.choice(["RS256", "ES256", "EdDSA"]),
            "session_duration_sec": random.randint(0, 86400),
            "concurrent_sessions": random.randint(1, 15) if is_attack else random.randint(1, 3),
            "geo_anomaly": is_attack and random.random() > 0.5,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L05_session_token_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L06 PKI — Certificate Issuance/Revocation Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l06_pki(n=2500):
    events = ["CERT_ISSUED", "CERT_REVOKED", "CERT_RENEWED", "OCSP_CHECK",
              "CHAIN_VALIDATION_FAILED", "WEAK_KEY_DETECTED", "CERT_EXPIRED_IN_USE",
              "ROGUE_CA_DETECTED", "CT_LOG_ANOMALY"]
    algorithms = ["RSA-2048", "RSA-4096", "EC-P256", "EC-P384", "ML-DSA-44", "ML-DSA-65", "SLH-DSA-128f"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.30, 0.15, 0.12, 0.20, 0.08, 0.06, 0.05, 0.02, 0.02])[0]
        is_attack = event in ("CHAIN_VALIDATION_FAILED", "WEAK_KEY_DETECTED",
                               "ROGUE_CA_DETECTED", "CT_LOG_ANOMALY")
        alg = random.choice(algorithms[:3]) if is_attack else random.choice(algorithms)
        key_size = {"RSA-2048": 2048, "RSA-4096": 4096, "EC-P256": 256, "EC-P384": 384,
                    "ML-DSA-44": 1312, "ML-DSA-65": 1952, "SLH-DSA-128f": 32}.get(alg, 2048)
        rows.append({
            "timestamp": rand_ts(),
            "serial_number": rand_hash(20),
            "subject_cn": f"service-{random.randint(1, 200)}.corp.internal",
            "issuer_cn": random.choice(["CorpRootCA", "IntermediateCA-1", "IntermediateCA-2"]),
            "event_type": event,
            "algorithm": alg,
            "key_size_bits": key_size,
            "validity_days": random.choice([90, 365, 730, 825]),
            "pqc_algorithm": alg in ("ML-DSA-44", "ML-DSA-65", "SLH-DSA-128f"),
            "ct_log_submitted": random.choice([True, False]),
            "ocsp_status": random.choice(["good", "revoked", "unknown"]),
            "san_count": random.randint(1, 8),
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L06_pki_cert_events.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L08 JWT — Token Validation Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l08_jwt(n=5000):
    events = ["TOKEN_VALID", "TOKEN_EXPIRED", "TOKEN_INVALID_SIG", "ALG_NONE_ATTACK",
              "ALG_CONFUSION_RS256_HS256", "KID_INJECTION", "JKU_SSRF_ATTEMPT",
              "EXCESSIVE_CLAIMS", "TOKEN_VALID"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.50, 0.15, 0.10, 0.06, 0.07, 0.05, 0.03, 0.02, 0.02])[0]
        is_attack = event in ("ALG_NONE_ATTACK", "ALG_CONFUSION_RS256_HS256",
                               "KID_INJECTION", "JKU_SSRF_ATTEMPT")
        rows.append({
            "timestamp": rand_ts(),
            "token_id": rand_hash(16),
            "client_ip": rand_ip(),
            "event_type": event,
            "algorithm_claimed": random.choice(["none", "HS256"]) if is_attack else random.choice(["RS256", "ES256", "EdDSA"]),
            "algorithm_expected": "RS256",
            "header_kid": f"../../../dev/null" if event == "KID_INJECTION" else rand_hash(8),
            "payload_size_bytes": random.randint(100, 4096),
            "num_claims": random.randint(1, 50) if event == "EXCESSIVE_CLAIMS" else random.randint(3, 12),
            "exp_delta_sec": random.randint(-3600, 86400),
            "iat_in_future": is_attack and random.random() > 0.7,
            "issuer": random.choice(["https://auth.corp.internal", "https://fake-issuer.attacker.com"]) if is_attack else "https://auth.corp.internal",
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L08_jwt_validation_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L09 DNS — Query Logs with DGA Detection
# ─────────────────────────────────────────────────────────────────────────────
def gen_l09_dns(n=6000):
    tlds = [".com", ".net", ".org", ".io", ".corp.internal"]
    legit_domains = ["google.com", "microsoft.com", "github.com", "aws.amazon.com",
                     "auth.corp.internal", "api.corp.internal", "mail.corp.internal"]
    events = ["QUERY_RESOLVED", "NXDOMAIN", "DGA_DETECTED", "DNS_TUNNELING",
              "CACHE_POISON_ATTEMPT", "DNSSEC_VALIDATION_FAILED", "QUERY_RESOLVED"]
    def dga_domain():
        length = random.randint(8, 24)
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.choice(chars) for _ in range(length)) + random.choice([".com", ".net", ".ru"])
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.55, 0.15, 0.10, 0.07, 0.05, 0.05, 0.03])[0]
        is_attack = event in ("DGA_DETECTED", "DNS_TUNNELING", "CACHE_POISON_ATTEMPT", "DNSSEC_VALIDATION_FAILED")
        domain = dga_domain() if is_attack else random.choice(legit_domains)
        entropy = sum(-p * math.log2(p) for c in set(domain) if (p := domain.count(c)/len(domain)) > 0)
        rows.append({
            "timestamp": rand_ts(),
            "client_ip": rand_ip(),
            "query_domain": domain,
            "query_type": random.choice(["A", "AAAA", "TXT", "MX", "CNAME", "NS"]),
            "response_code": random.choice(["NXDOMAIN", "SERVFAIL"]) if event == "DGA_DETECTED" else "NOERROR",
            "ttl_sec": random.randint(0, 86400),
            "domain_entropy": round(entropy, 4),
            "domain_length": len(domain),
            "consonant_vowel_ratio": round(random.uniform(1.5, 4.0) if is_attack else random.uniform(0.8, 2.0), 3),
            "event_type": event,
            "dnssec_validated": not is_attack,
            "resolver_ip": rand_ip(),
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L09_dns_query_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L10 SSH — Connection Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l10_ssh(n=4000):
    events = ["AUTH_SUCCESS", "AUTH_FAILURE", "BRUTE_FORCE_DETECTED", "KEY_TOO_WEAK",
              "AGENT_HIJACK_ATTEMPT", "ALGO_DOWNGRADE", "AUTH_SUCCESS", "PORT_FORWARD_BLOCKED"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.45, 0.25, 0.10, 0.06, 0.05, 0.04, 0.03, 0.02])[0]
        is_attack = event in ("BRUTE_FORCE_DETECTED", "KEY_TOO_WEAK",
                               "AGENT_HIJACK_ATTEMPT", "ALGO_DOWNGRADE")
        rows.append({
            "timestamp": rand_ts(),
            "client_ip": rand_ip(),
            "server_ip": rand_ip(),
            "server_port": 22,
            "event_type": event,
            "auth_method": random.choice(["password", "publickey", "none"]) if is_attack else random.choice(["publickey", "publickey", "keyboard-interactive"]),
            "kex_algorithm": random.choice(["diffie-hellman-group1-sha1", "diffie-hellman-group14-sha1"]) if is_attack else random.choice(["curve25519-sha256", "ecdh-sha2-nistp256"]),
            "host_key_type": random.choice(["ssh-rsa", "ssh-dss"]) if is_attack else random.choice(["ecdsa-sha2-nistp256", "ssh-ed25519"]),
            "host_key_bits": random.choice([512, 1024]) if is_attack else random.choice([256, 521]),
            "failed_attempts": random.randint(5, 500) if event == "BRUTE_FORCE_DETECTED" else random.randint(0, 3),
            "session_duration_sec": random.randint(0, 3600),
            "bytes_transferred": random.randint(0, 10_000_000),
            "pqc_kex_supported": event not in ("ALGO_DOWNGRADE",),
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L10_ssh_connection_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L11 Email — DKIM/DMARC/Phishing Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l11_email(n=5000):
    events = ["DELIVERED", "BLOCKED_SPAM", "PHISHING_DETECTED", "DKIM_FAIL",
              "DMARC_FAIL", "SPOOFED_SENDER", "MALICIOUS_ATTACHMENT", "BEC_SUSPECTED", "DELIVERED"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.45, 0.15, 0.10, 0.08, 0.07, 0.06, 0.05, 0.02, 0.02])[0]
        is_attack = event not in ("DELIVERED", "BLOCKED_SPAM")
        rows.append({
            "timestamp": rand_ts(),
            "message_id": f"<{rand_hash(16)}@mail.corp.internal>",
            "sender_domain": random.choice(["corp.internal", "attacker.ru", "amazon-support.phish.com", "microsoft.com"]) if is_attack else "corp.internal",
            "recipient_count": random.randint(1, 500) if is_attack else random.randint(1, 10),
            "event_type": event,
            "dkim_result": "fail" if event in ("DKIM_FAIL", "SPOOFED_SENDER") else "pass",
            "dmarc_result": "fail" if event in ("DMARC_FAIL", "SPOOFED_SENDER") else "pass",
            "spf_result": "fail" if is_attack and random.random() > 0.5 else "pass",
            "spam_score": round(random.uniform(6.0, 10.0) if is_attack else random.uniform(0.0, 4.0), 2),
            "attachment_count": random.randint(1, 5) if event == "MALICIOUS_ATTACHMENT" else random.randint(0, 2),
            "url_count": random.randint(3, 15) if event == "PHISHING_DETECTED" else random.randint(0, 5),
            "tls_encryption": random.choice([True, True, True, False]),
            "pqc_signing": False,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L11_email_security_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L12 CodeSign — Code Signing Audit Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l12_codesign(n=2000):
    events = ["SIGNATURE_VALID", "SIGNATURE_INVALID", "CERT_EXPIRED", "WEAK_HASH_SHA1",
              "UNSIGNED_BINARY", "TIMESTAMP_MISSING", "CROSS_CERT_ABUSE", "SIGNATURE_VALID"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.55, 0.12, 0.08, 0.08, 0.07, 0.05, 0.03, 0.02])[0]
        is_attack = event in ("SIGNATURE_INVALID", "WEAK_HASH_SHA1", "UNSIGNED_BINARY", "CROSS_CERT_ABUSE")
        rows.append({
            "timestamp": rand_ts(),
            "binary_hash": rand_hash(64),
            "binary_name": f"module_{random.randint(1,500)}.dll",
            "event_type": event,
            "signing_algorithm": random.choice(["sha1WithRSAEncryption", "md5WithRSAEncryption"]) if event == "WEAK_HASH_SHA1" else random.choice(["sha256WithRSAEncryption", "ecdsa-with-SHA256"]),
            "cert_issuer": random.choice(["DigiCert EV", "Sectigo", "GlobalSign", "Unknown CA"]),
            "cert_validity_remaining_days": random.randint(-365, 0) if event == "CERT_EXPIRED" else random.randint(1, 730),
            "timestamp_authority": "Digicert TSA" if event != "TIMESTAMP_MISSING" else None,
            "catalog_signed": random.choice([True, False]),
            "pqc_ready": event == "SIGNATURE_VALID" and random.random() > 0.8,
            "os_platform": random.choice(["Windows", "Linux", "macOS"]),
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L12_codesign_audit.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L13 VPN — Tunnel Connection Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l13_vpn(n=3500):
    events = ["TUNNEL_ESTABLISHED", "TUNNEL_CLOSED", "AUTH_FAILED", "CRED_STUFFING",
              "SPLIT_TUNNEL_VIOLATION", "IKE_DOWNGRADE", "PSK_WEAK", "TUNNEL_ESTABLISHED"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.40, 0.25, 0.12, 0.08, 0.06, 0.05, 0.02, 0.02])[0]
        is_attack = event in ("CRED_STUFFING", "SPLIT_TUNNEL_VIOLATION", "IKE_DOWNGRADE", "PSK_WEAK")
        rows.append({
            "timestamp": rand_ts(),
            "client_ip": rand_ip(),
            "client_vpn_ip": f"10.8.{random.randint(0,255)}.{random.randint(1,254)}",
            "server_ip": rand_ip(),
            "event_type": event,
            "ike_version": random.choice(["IKEv1", "IKEv2"]),
            "auth_method": random.choice(["PSK", "cert", "EAP-TLS"]),
            "cipher_suite": random.choice(["AES-128-CBC", "3DES"]) if is_attack else "AES-256-GCM",
            "dh_group": random.choice([1, 2, 5]) if event == "IKE_DOWNGRADE" else random.choice([14, 20, 21]),
            "tunnel_duration_sec": random.randint(0, 28800),
            "bytes_in": random.randint(0, 500_000_000),
            "bytes_out": random.randint(0, 100_000_000),
            "failed_auth_count": random.randint(50, 500) if event == "CRED_STUFFING" else 0,
            "pqc_ike_supported": event not in ("IKE_DOWNGRADE", "PSK_WEAK"),
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L13_vpn_tunnel_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L14 HSM — Hardware Security Module Operation Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l14_hsm(n=1500):
    events = ["KEY_GENERATED", "KEY_USED_ENCRYPT", "KEY_USED_SIGN", "KEY_DELETED",
              "PIN_ENTERED", "PIN_FAILED_3X_LOCKOUT", "FIRMWARE_UPDATE",
              "SIDE_CHANNEL_ANOMALY", "TAMPER_ALERT", "UNAUTHORIZED_SLOT_ACCESS"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.20, 0.25, 0.20, 0.05, 0.10, 0.06, 0.04, 0.04, 0.03, 0.03])[0]
        is_attack = event in ("PIN_FAILED_3X_LOCKOUT", "SIDE_CHANNEL_ANOMALY",
                               "TAMPER_ALERT", "UNAUTHORIZED_SLOT_ACCESS")
        rows.append({
            "timestamp": rand_ts(),
            "hsm_serial": f"HSM-{random.randint(1,5):02d}",
            "slot_id": random.randint(0, 15),
            "event_type": event,
            "key_label": f"key-{rand_hash(8)}",
            "key_algorithm": random.choice(["RSA-2048", "RSA-4096", "EC-P256", "AES-256", "ML-KEM-768", "ML-DSA-65"]),
            "key_length_bits": random.choice([2048, 4096, 256, 384, 3168, 1952]),
            "operation_duration_ms": round(random.uniform(0.5, 500), 3),
            "power_consumption_mw": round(random.uniform(180, 350) + (random.uniform(50, 200) if is_attack else 0), 2),
            "temperature_c": round(random.uniform(35, 45) + (random.uniform(5, 20) if is_attack else 0), 1),
            "tamper_sensors_active": is_attack,
            "operator_id": f"op_{random.randint(1,20):03d}",
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L14_hsm_operations.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L15 IAM — Identity & Access Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l15_iam(n=6000):
    events = ["LOGIN_SUCCESS", "LOGIN_FAILED", "MFA_BYPASS", "GOLDEN_TICKET",
              "PASS_THE_HASH", "PRIVILEGE_ESCALATION", "DORMANT_ACCOUNT_USED",
              "SERVICE_ACCOUNT_ABUSE", "LATERAL_MOVEMENT", "LOGIN_SUCCESS"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.40, 0.20, 0.08, 0.06, 0.06, 0.07, 0.05, 0.04, 0.02, 0.02])[0]
        is_attack = event in ("MFA_BYPASS", "GOLDEN_TICKET", "PASS_THE_HASH",
                               "PRIVILEGE_ESCALATION", "DORMANT_ACCOUNT_USED",
                               "SERVICE_ACCOUNT_ABUSE", "LATERAL_MOVEMENT")
        rows.append({
            "timestamp": rand_ts(),
            "user_id": f"user_{random.randint(1000, 9999)}",
            "client_ip": rand_ip(),
            "event_type": event,
            "auth_protocol": random.choice(["Kerberos", "NTLM", "SAML", "OAuth2", "LDAP"]),
            "mfa_used": not is_attack or random.random() > 0.8,
            "privilege_level": random.choice(["admin", "domain_admin", "system"]) if is_attack else random.choice(["user", "read_only"]),
            "ticket_lifetime_hours": random.choice([10, 20, 8760]) if event == "GOLDEN_TICKET" else 8,
            "src_workstation": f"WS-{random.randint(1, 500):04d}",
            "resource_accessed": random.choice(["DC01", "fileserver", "payroll_db", "source_code_repo"]) if is_attack else random.choice(["email", "sharepoint", "teams"]),
            "geo_location": random.choice(["CN", "RU", "KP", "IR"]) if is_attack else random.choice(["US", "CA", "UK"]),
            "risk_score": round(random.uniform(70, 100) if is_attack else random.uniform(0, 30), 1),
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L15_iam_access_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L16 API — Gateway Logs with Rate Limiting / BOLA
# ─────────────────────────────────────────────────────────────────────────────
def gen_l16_api(n=8000):
    endpoints = ["/api/v1/users/{id}", "/api/v1/accounts/{id}/balance",
                 "/api/v1/transactions", "/api/v1/admin/users", "/api/v1/health"]
    events = ["REQUEST_OK", "RATE_LIMITED", "AUTH_FAILED", "BOLA_DETECTED",
              "SQL_INJECTION_ATTEMPT", "MASS_ASSIGNMENT", "API_KEY_LEAKED",
              "EXCESSIVE_DATA_EXPOSURE", "REQUEST_OK"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.55, 0.12, 0.10, 0.07, 0.05, 0.04, 0.03, 0.02, 0.02])[0]
        is_attack = event in ("BOLA_DETECTED", "SQL_INJECTION_ATTEMPT",
                               "MASS_ASSIGNMENT", "API_KEY_LEAKED", "EXCESSIVE_DATA_EXPOSURE")
        rows.append({
            "timestamp": rand_ts(),
            "client_ip": rand_ip(),
            "method": random.choice(["GET", "POST", "PUT", "DELETE", "PATCH"]),
            "endpoint": random.choice(endpoints),
            "status_code": random.choice([200, 201]) if event == "REQUEST_OK" else random.choice([400, 401, 403, 429, 500]),
            "event_type": event,
            "response_time_ms": round(random.uniform(1, 5000), 2),
            "payload_size_bytes": random.randint(0, 10_000),
            "api_key_hash": rand_hash(16),
            "jwt_present": random.choice([True, False]),
            "requests_per_minute": random.randint(500, 10000) if event in ("RATE_LIMITED",) else random.randint(1, 60),
            "object_id_traversal": is_attack and event == "BOLA_DETECTED",
            "injection_payload": "' OR 1=1--" if event == "SQL_INJECTION_ATTEMPT" else None,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L16_api_gateway_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L18 Blockchain — Transaction Verification Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l18_blockchain(n=3000):
    events = ["TX_CONFIRMED", "TX_REJECTED", "DOUBLE_SPEND_ATTEMPT", "SMART_CONTRACT_VULN",
              "REENTRANCY_DETECTED", "QUANTUM_SIG_THREAT", "CONSENSUS_ANOMALY", "TX_CONFIRMED"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.55, 0.15, 0.08, 0.06, 0.05, 0.05, 0.04, 0.02])[0]
        is_attack = event in ("DOUBLE_SPEND_ATTEMPT", "SMART_CONTRACT_VULN",
                               "REENTRANCY_DETECTED", "QUANTUM_SIG_THREAT", "CONSENSUS_ANOMALY")
        rows.append({
            "timestamp": rand_ts(),
            "tx_hash": rand_hash(64),
            "block_height": random.randint(800000, 900000),
            "event_type": event,
            "signature_algorithm": random.choice(["ECDSA-secp256k1", "Ed25519"]) if not is_attack else "ECDSA-secp256k1",
            "sig_vulnerable_to_shor": not is_attack or True,
            "gas_used": random.randint(21000, 5_000_000),
            "value_eth": round(random.uniform(0, 10000), 6),
            "confirmations": random.randint(0, 2) if is_attack else random.randint(6, 100),
            "contract_address": f"0x{rand_hash(40)}" if "CONTRACT" in event or "REENTRANCY" in event else None,
            "pqc_signature_used": event != "QUANTUM_SIG_THREAT" and random.random() > 0.85,
            "network_hash_rate_pct_attacker": random.uniform(0, 30) if event == "CONSENSUS_ANOMALY" else 0,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L18_blockchain_tx_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L21 Mobile — Certificate Pinning / App Security Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l21_mobile(n=3000):
    events = ["APP_AUTH_OK", "CERT_PIN_BYPASS", "ROOT_JAILBREAK_DETECTED", "DYNAMIC_CODE_LOAD",
              "DEBUGGER_ATTACHED", "API_KEY_EXTRACTED", "SSL_STRIPPING", "APP_AUTH_OK"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.55, 0.10, 0.09, 0.08, 0.07, 0.05, 0.04, 0.02])[0]
        is_attack = event in ("CERT_PIN_BYPASS", "ROOT_JAILBREAK_DETECTED", "DYNAMIC_CODE_LOAD",
                               "DEBUGGER_ATTACHED", "API_KEY_EXTRACTED", "SSL_STRIPPING")
        rows.append({
            "timestamp": rand_ts(),
            "device_id": rand_hash(16),
            "platform": random.choice(["iOS", "Android"]),
            "app_version": f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}",
            "event_type": event,
            "cert_pin_match": not is_attack,
            "tls_version": "TLS1.2" if event == "SSL_STRIPPING" else "TLS1.3",
            "device_rooted": event in ("ROOT_JAILBREAK_DETECTED",),
            "frida_detected": event in ("CERT_PIN_BYPASS", "DEBUGGER_ATTACHED"),
            "obfuscation_detected": is_attack and random.random() > 0.6,
            "network_type": random.choice(["WiFi", "4G", "5G"]),
            "geo_country": random.choice(["CN", "RU"]) if is_attack else random.choice(["US", "CA", "UK"]),
            "pqc_tls_support": not is_attack and random.random() > 0.3,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L21_mobile_security_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L26 KMS — Key Management Rotation Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l26_kms(n=2000):
    events = ["KEY_ROTATED", "KEY_ACCESSED", "KEY_DELETED", "KEY_POLICY_CHANGED",
              "UNAUTHORIZED_DECRYPT", "KEY_EXPORT_ATTEMPT", "STALE_KEY_ALERT",
              "QUANTUM_HARVEST_WINDOW", "KEY_ROTATED"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.25, 0.35, 0.05, 0.10, 0.08, 0.05, 0.05, 0.05, 0.02])[0]
        is_attack = event in ("UNAUTHORIZED_DECRYPT", "KEY_EXPORT_ATTEMPT",
                               "QUANTUM_HARVEST_WINDOW", "STALE_KEY_ALERT")
        rows.append({
            "timestamp": rand_ts(),
            "key_id": f"arn:aws:kms:us-east-1:123456789012:key/{uuid.uuid4()}",
            "event_type": event,
            "key_algorithm": random.choice(["RSA-2048", "RSA-4096", "AES-256"]) if is_attack else random.choice(["AES-256-GCM", "ML-KEM-768", "ML-DSA-65"]),
            "key_age_days": random.randint(180, 3650) if is_attack else random.randint(0, 90),
            "last_rotation_days": random.randint(90, 1000) if event == "STALE_KEY_ALERT" else random.randint(0, 90),
            "caller_iam_arn": f"arn:aws:iam::123456789012:user/{'attacker' if is_attack else f'svc-{random.randint(1,20)}'}",
            "key_usage": random.choice(["ENCRYPT_DECRYPT", "SIGN_VERIFY"]),
            "compliance_pci_dss": not is_attack,
            "quantum_harvest_risk": event == "QUANTUM_HARVEST_WINDOW",
            "cross_account_access": is_attack and random.random() > 0.5,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L26_kms_key_events.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L27 Compliance — Regulatory Audit Events
# ─────────────────────────────────────────────────────────────────────────────
def gen_l27_compliance(n=2000):
    frameworks = ["PCI-DSS v4.0", "SOC 2 Type II", "ISO 27001:2022", "NIST CSF 2.0",
                  "CNSA 2.0", "FIPS 140-3", "GDPR"]
    events = ["CONTROL_PASSED", "CONTROL_FAILED", "FINDING_OPENED", "FINDING_CLOSED",
              "EVIDENCE_TAMPERED", "AUDIT_LOG_DELETED", "POLICY_OVERRIDE", "CONTROL_PASSED"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.45, 0.20, 0.12, 0.10, 0.04, 0.04, 0.03, 0.02])[0]
        is_attack = event in ("EVIDENCE_TAMPERED", "AUDIT_LOG_DELETED", "POLICY_OVERRIDE")
        rows.append({
            "timestamp": rand_ts(),
            "framework": random.choice(frameworks),
            "control_id": f"CC{random.randint(1,9)}.{random.randint(1,9)}",
            "event_type": event,
            "control_description": random.choice([
                "Cryptographic key management", "Access control review",
                "Incident response procedure", "Vulnerability scanning",
                "PQC algorithm inventory", "CBOM completeness check"]),
            "finding_severity": random.choice(["Critical", "High", "Medium", "Low"]),
            "pqc_relevant": random.random() > 0.4,
            "cnsa_20_compliant": not is_attack and random.random() > 0.5,
            "evidence_hash": rand_hash(32),
            "auditor_id": f"auditor_{random.randint(1,10)}",
            "remediation_days": random.randint(0, 90) if event == "FINDING_OPENED" else 0,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L27_compliance_audit_events.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L28 Audit — Tamper-Evident Log Trail
# ─────────────────────────────────────────────────────────────────────────────
def gen_l28_audit(n=3000):
    events = ["LOG_ENTRY_OK", "LOG_TAMPERED", "LOG_DELETED", "LOG_FORWARDING_INTERRUPTED",
              "TIMESTAMP_ANOMALY", "HASH_CHAIN_BROKEN", "WORM_BYPASS_ATTEMPTED", "LOG_ENTRY_OK"]
    rows = []
    prev_hash = rand_hash(64)
    for i in range(n):
        event = random.choices(events, weights=[0.60, 0.08, 0.07, 0.07, 0.06, 0.06, 0.04, 0.02])[0]
        is_attack = event in ("LOG_TAMPERED", "LOG_DELETED", "HASH_CHAIN_BROKEN", "WORM_BYPASS_ATTEMPTED")
        current_hash = rand_hash(64) if is_attack else hashlib.sha256(prev_hash.encode()).hexdigest()
        rows.append({
            "timestamp": rand_ts(),
            "log_sequence_id": i + 1,
            "event_type": event,
            "entry_hash": current_hash,
            "prev_hash": prev_hash,
            "hash_valid": not is_attack,
            "source_system": random.choice(["firewall-01", "web-proxy", "siem-core", "hsm-01", "kms-01"]),
            "log_level": random.choice(["INFO", "WARN", "ERROR", "CRITICAL"]),
            "syslog_facility": random.randint(0, 23),
            "forwarded_to_siem": event != "LOG_FORWARDING_INTERRUPTED",
            "worm_storage": event != "WORM_BYPASS_ATTEMPTED",
            "retention_days": 2555,
            "label": "attack" if is_attack else "normal",
        })
        prev_hash = current_hash
    write_csv("L28_audit_log_chain.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# L29 AI/ML — Model Security / Adversarial Attack Logs
# ─────────────────────────────────────────────────────────────────────────────
def gen_l29_aiml(n=3000):
    events = ["INFERENCE_OK", "ADVERSARIAL_EXAMPLE_DETECTED", "MODEL_EXTRACTION",
              "DATA_POISONING_SUSPECTED", "PROMPT_INJECTION", "MODEL_INVERSION",
              "MEMBERSHIP_INFERENCE", "BACKDOOR_TRIGGER", "INFERENCE_OK"]
    rows = []
    for _ in range(n):
        event = random.choices(events, weights=[0.55, 0.10, 0.08, 0.08, 0.07, 0.05, 0.04, 0.01, 0.02])[0]
        is_attack = event not in ("INFERENCE_OK",)
        rows.append({
            "timestamp": rand_ts(),
            "model_id": f"model-{random.choice(['fraud-detect-v2', 'ids-classifier-v3', 'anomaly-v1', 'llm-gateway-v1'])}",
            "event_type": event,
            "confidence_score": round(random.uniform(0.3, 0.7) if is_attack else random.uniform(0.7, 1.0), 4),
            "prediction": random.choice(["benign", "anomaly"]),
            "input_perturbation_norm": round(random.uniform(0.01, 2.0) if is_attack else random.uniform(0, 0.001), 6),
            "query_count_last_1h": random.randint(100, 10000) if event == "MODEL_EXTRACTION" else random.randint(1, 50),
            "training_data_anomaly_score": round(random.uniform(0.5, 1.0) if event == "DATA_POISONING_SUSPECTED" else random.uniform(0, 0.3), 4),
            "prompt_contains_injection": event == "PROMPT_INJECTION",
            "model_framework": random.choice(["PyTorch", "TensorFlow", "sklearn", "LangChain"]),
            "differential_privacy_epsilon": round(random.uniform(0.1, 10.0), 3),
            "pqc_model_signing": random.random() > 0.7,
            "label": "attack" if is_attack else "normal",
        })
    write_csv("L29_aiml_security_logs.csv", rows, list(rows[0].keys()))

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Generating Synthetic Security Datasets ===\n")
    gen_l01_physical()
    gen_l02_macsec()
    gen_l05_session()
    gen_l06_pki()
    gen_l08_jwt()
    gen_l09_dns()
    gen_l10_ssh()
    gen_l11_email()
    gen_l12_codesign()
    gen_l13_vpn()
    gen_l14_hsm()
    gen_l15_iam()
    gen_l16_api()
    gen_l18_blockchain()
    gen_l21_mobile()
    gen_l26_kms()
    gen_l27_compliance()
    gen_l28_audit()
    gen_l29_aiml()

    # Print summary
    files = list(ROOT.glob("*.csv"))
    total_rows = 0
    print(f"\n=== Summary ===")
    for f in sorted(files):
        with open(f) as fp:
            rows = sum(1 for _ in fp) - 1
            total_rows += rows
            size_kb = f.stat().st_size // 1024
            print(f"  {f.name:<45} {rows:>5} rows  {size_kb:>5} KB")
    print(f"\n  Total: {len(files)} files, {total_rows:,} rows\n")

    # Write manifest
    manifest = []
    for f in sorted(files):
        with open(f) as fp:
            reader = csv.DictReader(fp)
            fieldnames = reader.fieldnames or []
        manifest.append({"file": f.name, "size_bytes": f.stat().st_size,
                         "columns": fieldnames})
    with open(ROOT / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifest written: {ROOT}/manifest.json\n")
