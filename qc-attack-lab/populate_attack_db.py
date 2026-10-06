#!/usr/bin/env python3
"""
Populate attack_logs.db with realistic attack simulation data.
Run: python3 populate_attack_db.py
"""
import sys
import pathlib
import random
import datetime
import hashlib
import sqlite3
import os

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

# ── Try to use AttackLogger; fall back to direct SQLite ───────────────────────
try:
    from attack_logger import AttackLogger, DB_PATH
    _USE_LOGGER = True
except Exception as e:
    print(f"  [warn] Could not import AttackLogger ({e}); using direct SQLite.")
    _USE_LOGGER = False
    DB_PATH = ROOT / "results" / "attack_logs.db"

# ── DB bootstrap (used when AttackLogger unavailable) ─────────────────────────

def _ensure_db(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attack_logs (
            log_id           TEXT PRIMARY KEY,
            timestamp        TEXT NOT NULL,
            layer_id         TEXT NOT NULL,
            layer_name       TEXT NOT NULL,
            attack_name      TEXT NOT NULL,
            cve              TEXT DEFAULT 'N/A',
            tool_used        TEXT,
            mitre_technique  TEXT,
            source_system    TEXT,
            target_system    TEXT,
            severity         TEXT,
            status           TEXT,
            classical_result TEXT,
            pqc_result       TEXT,
            evidence         TEXT,
            detection_method TEXT,
            response_action  TEXT,
            ttd_seconds      REAL DEFAULT -1,
            ttr_seconds      REAL DEFAULT -1,
            analyst          TEXT,
            notes            TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_layer    ON attack_logs(layer_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ts       ON attack_logs(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON attack_logs(severity)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status   ON attack_logs(status)")
    conn.commit()
    return conn


def _make_id(ts: str, layer_id: str, attack_name: str) -> str:
    raw = f"{ts}{layer_id}{attack_name}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Layer definitions (29 layers) ─────────────────────────────────────────────

LAYERS = [
    ("L01", "Physical / Hardware"),
    ("L02", "Data Link / MACsec"),
    ("L03", "IPsec / VPN"),
    ("L04", "TLS / HTTPS"),
    ("L05", "Session / Token"),
    ("L06", "PKI / Certificate"),
    ("L07", "Application / WAF"),
    ("L08", "JWT / OAuth"),
    ("L09", "DNS / DNSSEC"),
    ("L10", "SSH"),
    ("L11", "Email / S/MIME"),
    ("L12", "Code Signing"),
    ("L13", "VPN Overlay"),
    ("L14", "Key Management"),
    ("L15", "IAM / LDAP"),
    ("L16", "API Gateway"),
    ("L17", "Database / TDE"),
    ("L18", "Blockchain"),
    ("L19", "Service Mesh"),
    ("L20", "IoT / DTLS"),
    ("L21", "Mobile / Cert Pin"),
    ("L22", "Firmware / TPM"),
    ("L23", "CI/CD Pipeline"),
    ("L24", "SIEM / Logging"),
    ("L25", "Zero Trust"),
    ("L26", "Container / k8s"),
    ("L27", "Cloud IAM"),
    ("L28", "Quantum Channel"),
    ("L29", "PQC Migration"),
]

# ── Attack catalogue per layer ────────────────────────────────────────────────

LAYER_ATTACKS = {
    "L01": [
        ("TPM Seal Bypass", "N/A", "tpm-exploit", "T1542.001", False),
        ("PRNG Seed Prediction", "N/A", "entropy-harvest", "T1600", False),
        ("Cold Boot Attack", "N/A", "cold-boot-kit", "T1006", False),
        ("HSM Fault Injection", "CVE-2022-21449", "voltglitch", "T1542", False),
        ("Firmware Downgrade", "CVE-2020-5953", "dfu-exploit", "T1542.001", False),
    ],
    "L02": [
        ("ARP Spoofing", "N/A", "arpspoof", "T1557.002", False),
        ("MACsec Key Roll Bypass", "N/A", "macsec-tool", "T1557", False),
        ("WPA3 Downgrade (Dragonblood)", "CVE-2019-9494", "dragonblood", "T1557.004", False),
        ("VLAN Hopping", "N/A", "yersinia", "T1599", False),
        ("EAP-TLS Cert Replay", "N/A", "hostapd-evil", "T1557", False),
    ],
    "L03": [
        ("IKEv2 Aggressive Mode", "CVE-2018-7182", "ike-scan", "T1190", False),
        ("DH-2048 Quantum Simulation", "N/A", "Shor-sim", "T1557", True),
        ("IPsec SA Replay", "N/A", "ipsec-replay", "T1557.001", False),
        ("IKEv1 Downgrade", "N/A", "ikeforce", "T1562.010", False),
        ("VPN Credential Brute Force", "N/A", "hydra", "T1110.003", False),
    ],
    "L04": [
        ("HNDL — Harvest Now Decrypt Later", "N/A", "HNDL-collector", "T1557", True),
        ("POODLE Attack", "CVE-2014-3566", "poodle-poc", "T1557.004", False),
        ("BEAST Attack", "CVE-2011-3389", "beast-poc", "T1557.004", False),
        ("Certificate Forgery", "N/A", "fakecert", "T1553.004", False),
        ("HPKP Bypass", "N/A", "hpkp-pin-bypass", "T1553.004", False),
        ("TLS 1.0 Downgrade", "N/A", "sslstrip2", "T1562.010", False),
        ("Heartbleed", "CVE-2014-0160", "heartbleed-poc", "T1190", False),
        ("ROBOT Attack", "CVE-2017-17382", "robot-attack", "T1557", False),
    ],
    "L05": [
        ("Session Fixation", "N/A", "session-fixation", "T1539", False),
        ("JWT None Algorithm", "N/A", "jwt-tool", "T1550.001", False),
        ("HMAC Timing Attack", "N/A", "timing-atk", "T1556", False),
        ("Redis Key Theft", "N/A", "redis-rogue", "T1213", False),
        ("Session Token Prediction", "N/A", "tokenpred", "T1539", False),
    ],
    "L06": [
        ("Weak RSA-1024 Key", "N/A", "rsa-factoring", "T1600", True),
        ("Certificate Expiry Exploitation", "N/A", "cert-exploit", "T1553.004", False),
        ("Rogue CA Certificate", "N/A", "rouge-ca", "T1553.004", False),
        ("CT Log Anomaly", "N/A", "ct-monitor", "T1040", False),
        ("OCSP Replay", "N/A", "ocsp-replay", "T1557", False),
        ("CA Private Key Theft", "N/A", "key-exfil", "T1552.004", True),
    ],
    "L07": [
        ("SQL Injection via API", "N/A", "sqlmap", "T1190", False),
        ("XXE Injection", "N/A", "xxe-tool", "T1190", False),
        ("SSRF Attack", "N/A", "ssrf-tool", "T1602", False),
        ("WAF Bypass via Encoding", "N/A", "wafbypass", "T1027", False),
        ("Path Traversal", "N/A", "dotdotpwn", "T1083", False),
    ],
    "L08": [
        ("JWT Algorithm Confusion", "N/A", "jwt-tool", "T1550.001", False),
        ("OAuth Token Theft", "N/A", "evilginx2", "T1539", False),
        ("RS256 to HS256 Switch", "N/A", "jwt-tool", "T1550.001", False),
        ("Open Redirect OAuth", "N/A", "open-redirect", "T1550.001", False),
        ("JWT Key Injection", "N/A", "jwt-key-inject", "T1550.001", False),
    ],
    "L09": [
        ("DNS Cache Poisoning", "CVE-2020-1350", "dnspwn", "T1584.002", False),
        ("DGA Domain Registration", "N/A", "dga-gen", "T1583.001", False),
        ("DNS Tunneling", "N/A", "iodine", "T1071.004", False),
        ("DNSSEC Downgrade", "N/A", "dnssec-strip", "T1562.010", False),
        ("NXDOMAIN Amplification", "N/A", "dns-amp", "T1498.002", False),
    ],
    "L10": [
        ("SSH Brute Force", "N/A", "hydra", "T1110.003", False),
        ("Weak Cipher Negotiation", "N/A", "ssh-audit", "T1600", False),
        ("Terrapin Attack", "CVE-2023-48795", "terrapin-scan", "T1557", False),
        ("SSH Key Theft", "N/A", "key-exfil", "T1552.004", False),
        ("Root Login Attempt", "N/A", "hydra-root", "T1078.003", False),
        ("SSH Protocol Downgrade", "N/A", "ssh1-scan", "T1562.010", False),
    ],
    "L11": [
        ("DKIM Replay Attack", "N/A", "dkim-replay", "T1566.001", False),
        ("SPF Bypass", "N/A", "spf-bypass", "T1566.001", False),
        ("PGP Key Expiry Exploit", "N/A", "pgp-expired", "T1553.004", False),
        ("Email Spoofing", "N/A", "swaks", "T1566.001", False),
        ("DMARC Bypass", "N/A", "dmarc-bypass", "T1566", False),
    ],
    "L12": [
        ("Code Signing Key Theft", "N/A", "key-exfil", "T1553.002", True),
        ("Supply Chain Package Injection", "N/A", "dep-confusion", "T1195.002", False),
        ("Unsigned Commit Push", "N/A", "git-push", "T1195.002", False),
        ("Sigstore Transparency Log Spoof", "N/A", "rekor-spoof", "T1553.002", False),
        ("CI/CD Pipeline Injection", "N/A", "ci-inject", "T1195.002", False),
    ],
    "L13": [
        ("WireGuard Key Compromise", "N/A", "wg-privkey", "T1552.004", True),
        ("OpenVPN BF-CBC Exploit", "N/A", "openvpn-exploit", "T1557", False),
        ("Split Tunnel Bypass", "N/A", "split-bypass", "T1599", False),
        ("VPN DH Group Downgrade", "N/A", "dh-downgrade", "T1562.010", False),
    ],
    "L14": [
        ("HashiCorp Vault Seal Bypass", "CVE-2022-40186", "vault-exploit", "T1552.001", False),
        ("HSM Key Extraction", "N/A", "hsm-exfil", "T1552.004", True),
        ("PKCS11 Token Clone", "N/A", "pkcs11-clone", "T1552.004", True),
        ("Key Rotation Race", "N/A", "key-race", "T1600", False),
        ("Quantum Key Harvest (HNDL)", "N/A", "HNDL-km", "T1557", True),
    ],
    "L15": [
        ("Golden Ticket Attack", "N/A", "mimikatz", "T1558.001", False),
        ("Pass-the-Hash", "N/A", "pth-toolkit", "T1550.002", False),
        ("LDAP Injection", "N/A", "ldap-inject", "T1190", False),
        ("MFA Bypass via SS7", "N/A", "ss7-tool", "T1621", False),
        ("Kerberoasting", "N/A", "rubeus", "T1558.003", False),
        ("Privilege Escalation via OIDC", "N/A", "oidc-priv", "T1078", False),
    ],
    "L16": [
        ("API Key Brute Force", "N/A", "api-brute", "T1110.003", False),
        ("mTLS Client Cert Replay", "N/A", "mtls-replay", "T1557", False),
        ("GraphQL Introspection Attack", "N/A", "gql-introspect", "T1046", False),
        ("Rate Limit Bypass", "N/A", "ratelimit-bypass", "T1499.002", False),
        ("JWT RS256 Key Confusion", "N/A", "jwt-tool", "T1550.001", False),
    ],
    "L17": [
        ("TDE Key Extraction", "N/A", "tde-key-exfil", "T1552.004", True),
        ("SQL Injection (DB Level)", "N/A", "sqlmap", "T1190", False),
        ("Plaintext DB Connection", "N/A", "tcp-hijack", "T1557", False),
        ("DB Credential Theft", "N/A", "db-enum", "T1552.001", False),
        ("Column Decryption Attack", "N/A", "col-decrypt", "T1048", True),
    ],
    "L18": [
        ("Bitcoin P2PK Quantum Threat", "N/A", "Shor-ecc-sim", "T1557", True),
        ("ECDSA Nonce Reuse", "N/A", "nonce-reuse", "T1600", True),
        ("51% Attack Simulation", "N/A", "51pct-sim", "T1499", False),
        ("Blockchain Address Reuse", "N/A", "addr-reuse", "T1557", True),
        ("Smart Contract Exploit", "N/A", "reentrancy", "T1190", False),
    ],
    "L19": [
        ("mTLS Cert Spoof in Mesh", "N/A", "mesh-spoof", "T1557", False),
        ("SVID Expiry Exploit", "N/A", "svid-exploit", "T1134", False),
        ("Istio Policy Bypass", "N/A", "istio-bypass", "T1562", False),
        ("Sidecar Injection Attack", "N/A", "sidecar-inject", "T1610", False),
    ],
    "L20": [
        ("DTLS 1.0 Downgrade", "CVE-2019-0201", "dtls-strip", "T1562.010", False),
        ("MQTT Plaintext Sniff", "N/A", "mqtt-sniff", "T1040", False),
        ("Firmware OTA Manipulation", "N/A", "ota-tamper", "T1542.001", False),
        ("IoT Key Hardcoded Theft", "N/A", "binwalk", "T1552.001", False),
    ],
    "L21": [
        ("Certificate Pinning Bypass", "N/A", "frida", "T1553.004", False),
        ("SSL Kill Switch", "N/A", "ssl-kill", "T1553.004", False),
        ("TLS Downgrade on Mobile", "N/A", "sslstrip-mobile", "T1562.010", False),
        ("Root CA Import Attack", "N/A", "ca-import", "T1553.004", False),
    ],
    "L22": [
        ("TPM PCR Spoofing", "N/A", "pcr-spoof", "T1542.001", False),
        ("Secure Boot Disable", "CVE-2023-21608", "bootkit", "T1542.003", False),
        ("Keylime Attestation Bypass", "N/A", "keylime-bypass", "T1542", False),
        ("UEFI Firmware Tamper", "N/A", "uefi-tamper", "T1542.001", False),
    ],
    "L23": [
        ("Dependency Confusion Attack", "N/A", "dep-confusion", "T1195.002", False),
        ("CI Secret Exfil", "N/A", "env-exfil", "T1552.007", False),
        ("Container Escape via CVE", "CVE-2022-0847", "dirtypipe", "T1611", False),
        ("Pipeline Injection via PR", "N/A", "pr-inject", "T1195.002", False),
        ("SBOM Tampering", "N/A", "sbom-tamper", "T1553.002", False),
    ],
    "L24": [
        ("SIEM Log Deletion", "N/A", "log-delete", "T1070.001", False),
        ("Log Injection Attack", "N/A", "log-inject", "T1027", False),
        ("Log Shipper TLS Downgrade", "N/A", "beats-strip", "T1562.010", False),
        ("Wazuh Agent Spoof", "N/A", "wazuh-spoof", "T1078", False),
    ],
    "L25": [
        ("Zero Trust Policy Bypass", "N/A", "zt-bypass", "T1562", False),
        ("SPIFFE SVID Forge", "N/A", "svid-forge", "T1134", False),
        ("BeyondCorp Relay Attack", "N/A", "relay-atk", "T1557", False),
        ("Cilium eBPF Policy Bypass", "N/A", "ebpf-bypass", "T1562", False),
    ],
    "L26": [
        ("kubectl Secret Dump", "N/A", "kubectl-dump", "T1552.007", False),
        ("Kubernetes RBAC Escalation", "N/A", "k8s-rbac", "T1078.003", False),
        ("Container Image Supply Chain", "N/A", "image-tamper", "T1195.002", False),
        ("etcd Data Exfil", "N/A", "etcd-exfil", "T1213", False),
        ("Admission Webhook Bypass", "N/A", "webhook-bypass", "T1562", False),
    ],
    "L27": [
        ("IAM Role Assumption Chain", "N/A", "pacu", "T1078.004", False),
        ("Cloud Metadata SSRF", "N/A", "imds-ssrf", "T1552.005", False),
        ("Storage Bucket Misconfiguration", "N/A", "bucket-enum", "T1530", False),
        ("Service Account Key Theft", "N/A", "sa-key-exfil", "T1552.004", True),
        ("Cloud KMS Key Access", "N/A", "kms-access", "T1552.004", True),
    ],
    "L28": [
        ("Intercept-Resend BB84", "N/A", "qkd-intercept", "T1557", False),
        ("Photon Number Splitting", "N/A", "pns-attack", "T1557", False),
        ("Trojan State Attack", "N/A", "trojan-state", "T1557", False),
        ("QKD Denial of Service", "N/A", "qkd-dos", "T1499", False),
    ],
    "L29": [
        ("PQC Algorithm Downgrade", "N/A", "pqc-downgrade", "T1562.010", False),
        ("CRYSTALS-Kyber Side Channel", "CVE-2023-29360", "kyber-sca", "T1600", True),
        ("Hybrid TLS PQC Bypass", "N/A", "hybrid-bypass", "T1557", False),
        ("ML-KEM Key Recovery", "N/A", "kyber-recover", "T1600", True),
        ("NIST PQC Migration Race", "N/A", "migration-race", "T1600", False),
    ],
}

SEVERITY_WEIGHTS = ["CRITICAL"] * 20 + ["HIGH"] * 35 + ["MEDIUM"] * 30 + ["LOW"] * 15
STATUSES = ["DETECTED"] * 45 + ["BLOCKED"] * 30 + ["ATTEMPTED"] * 10 + \
           ["PARTIAL"] * 8 + ["SUCCESS"] * 5 + ["ONGOING"] * 2
ANALYSTS = ["SOC-L1"] * 40 + ["SOC-L2"] * 30 + ["AUTOMATED"] * 30
SOURCES = ["S1", "S2", "S3", "S4"]
TARGETS = ["S3 Classical", "S4 PQC", "S2 Network", "S1 Perimeter"]

MITRE_TACTICS = {
    "T1190": "Initial Access", "T1557": "Credential Access",
    "T1552": "Credential Access", "T1110": "Credential Access",
    "T1599": "Defense Evasion", "T1562": "Defense Evasion",
    "T1553": "Defense Evasion", "T1070": "Defense Evasion",
    "T1542": "Persistence", "T1558": "Credential Access",
    "T1550": "Lateral Movement", "T1611": "Privilege Escalation",
    "T1600": "Defense Evasion", "T1195": "Initial Access",
    "T1046": "Discovery", "T1040": "Discovery",
    "T1083": "Discovery", "T1213": "Collection",
    "T1530": "Collection", "T1048": "Exfiltration",
    "T1539": "Credential Access", "T1498": "Impact",
    "T1499": "Impact", "T1027": "Defense Evasion",
    "T1566": "Initial Access", "T1602": "Collection",
    "T1621": "Credential Access", "T1078": "Defense Evasion",
    "T1134": "Privilege Escalation", "T1610": "Defense Evasion",
    "T1071": "Command and Control", "T1583": "Resource Development",
    "T1584": "Resource Development",
}

DETECTION_METHODS = [
    "IDS signature match", "SIEM correlation rule", "Anomaly detection ML model",
    "Threat intelligence feed", "Manual SOC review", "Automated honeypot trigger",
    "WAF rule hit", "Endpoint detection agent", "Network flow analysis",
    "Log aggregation alert", "Quantum threat scanner", "Certificate transparency monitor",
]

RESPONSE_ACTIONS = [
    "Blocked source IP; alert SOC", "Ticket created P1; patched within 4h",
    "Key rotation initiated", "Alert forwarded to SOC-L2", "Session terminated",
    "Certificate revoked and reissued", "Firewall rule updated", "Service isolated",
    "Credential reset forced", "Emergency change window opened",
    "PQC migration accelerated for affected component", "Forensic capture initiated",
]

PCAP_NAMES = [
    "traffic_capture.pcap", "hndl_stream.pcap", "tls_probe_443.pcap",
    "ssh_bruteforce.pcap", "dns_tunnel.pcap", "arp_spoof.pcap",
    "ike_handshake.pcap", "jwt_replay.pcap", "mtls_handshake.pcap",
    "qkd_intercept.pcap",
]


def _random_timestamp(rng: random.Random, days_back: int = 30) -> str:
    """Generate a realistic timestamp — higher density on weekday business hours."""
    now = datetime.datetime.utcnow()
    # Pick a random moment in the last days_back days
    delta_seconds = rng.randint(0, days_back * 86400)
    ts = now - datetime.timedelta(seconds=delta_seconds)
    # Bias toward business hours weekdays (Mon-Fri 07-19 UTC)
    if rng.random() < 0.65 and ts.weekday() < 5:
        # Keep weekday; shift hour toward business window
        hour = rng.randint(7, 18)
        ts = ts.replace(hour=hour, minute=rng.randint(0, 59),
                        second=rng.randint(0, 59), microsecond=0)
    return ts.isoformat()


def _make_evidence(rng: random.Random, attack_name: str, layer_id: str) -> str:
    import json
    return json.dumps({
        "pcap": rng.choice(PCAP_NAMES),
        "hash": hashlib.sha256(
            f"{attack_name}{layer_id}{rng.random()}".encode()
        ).hexdigest()[:16],
        "log_extract": (
            f"{attack_name} observed from "
            f"10.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}; "
            f"layer {layer_id}"
        ),
    })


def _ttd_seconds(rng: random.Random, status: str) -> float:
    """Time-to-detect: exponential distribution, -1 if missed."""
    if status in ("SUCCESS",):
        # Attack succeeded — may have been detected late or not at all
        return round(rng.expovariate(1 / 3600) + 60, 1) if rng.random() < 0.5 else -1
    return round(rng.expovariate(1 / 900) + 30, 1)   # avg ~15 min, min 30s


def _ttr_seconds(rng: random.Random, severity: str, ttd: float) -> float:
    """Time-to-respond: depends on severity."""
    base = {"CRITICAL": 1800, "HIGH": 3600, "MEDIUM": 7200, "LOW": 14400}.get(severity, 3600)
    noise = rng.gauss(base, base * 0.3)
    return round(max(900, noise + (ttd if ttd > 0 else 0)), 1)


def generate_entries(n: int = 600, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    entries: list[dict] = []

    # Ensure at least one entry per layer
    for layer_id, layer_name in LAYERS:
        attacks = LAYER_ATTACKS.get(layer_id, [])
        if not attacks:
            continue
        atk_name, cve, tool, mitre, pqc_relevant = rng.choice(attacks)
        ts = _random_timestamp(rng)
        severity = rng.choice(SEVERITY_WEIGHTS)
        status = rng.choice(STATUSES)
        ttd = _ttd_seconds(rng, status)
        ttr = _ttr_seconds(rng, severity, ttd)
        entries.append({
            "log_id":           _make_id(ts, layer_id, atk_name + str(rng.random())),
            "timestamp":        ts,
            "layer_id":         layer_id,
            "layer_name":       layer_name,
            "attack_name":      atk_name,
            "cve":              cve,
            "tool_used":        tool,
            "mitre_technique":  mitre,
            "source_system":    rng.choice(SOURCES),
            "target_system":    rng.choice(TARGETS),
            "severity":         severity,
            "status":           status,
            "classical_result": f"Classical system {'VULNERABLE' if status != 'BLOCKED' else 'PROTECTED'} to {atk_name}",
            "pqc_result":       ("PQC PREVENTS: quantum-safe algorithm active" if pqc_relevant
                                 else "PQC N/A for this attack class"),
            "evidence":         _make_evidence(rng, atk_name, layer_id),
            "detection_method": rng.choice(DETECTION_METHODS),
            "response_action":  rng.choice(RESPONSE_ACTIONS),
            "ttd_seconds":      ttd,
            "ttr_seconds":      ttr,
            "analyst":          rng.choice(ANALYSTS),
            "notes":            f"Automated simulation entry — {layer_name} / {atk_name}",
        })

    # Fill remaining entries randomly across all layers
    while len(entries) < n:
        layer_id, layer_name = rng.choice(LAYERS)
        attacks = LAYER_ATTACKS.get(layer_id, [])
        if not attacks:
            continue
        atk_name, cve, tool, mitre, pqc_relevant = rng.choice(attacks)
        ts = _random_timestamp(rng)
        severity = rng.choice(SEVERITY_WEIGHTS)
        status = rng.choice(STATUSES)
        ttd = _ttd_seconds(rng, status)
        ttr = _ttr_seconds(rng, severity, ttd)
        entries.append({
            "log_id":           _make_id(ts, layer_id, atk_name + str(rng.random())),
            "timestamp":        ts,
            "layer_id":         layer_id,
            "layer_name":       layer_name,
            "attack_name":      atk_name,
            "cve":              cve,
            "tool_used":        tool,
            "mitre_technique":  mitre,
            "source_system":    rng.choice(SOURCES),
            "target_system":    rng.choice(TARGETS),
            "severity":         severity,
            "status":           status,
            "classical_result": f"Classical system {'VULNERABLE' if status != 'BLOCKED' else 'PROTECTED'} to {atk_name}",
            "pqc_result":       ("PQC PREVENTS: quantum-safe algorithm active" if pqc_relevant
                                 else "PQC N/A for this attack class"),
            "evidence":         _make_evidence(rng, atk_name, layer_id),
            "detection_method": rng.choice(DETECTION_METHODS),
            "response_action":  rng.choice(RESPONSE_ACTIONS),
            "ttd_seconds":      ttd,
            "ttr_seconds":      ttr,
            "analyst":          rng.choice(ANALYSTS),
            "notes":            f"Automated simulation entry — {layer_name} / {atk_name}",
        })

    return entries


def insert_entries_direct(entries: list[dict], db_path: pathlib.Path) -> None:
    conn = _ensure_db(db_path)
    inserted = 0
    for e in entries:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO attack_logs VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                e["log_id"], e["timestamp"], e["layer_id"], e["layer_name"],
                e["attack_name"], e["cve"], e["tool_used"], e["mitre_technique"],
                e["source_system"], e["target_system"], e["severity"], e["status"],
                e["classical_result"], e["pqc_result"], e["evidence"],
                e["detection_method"], e["response_action"],
                e["ttd_seconds"], e["ttr_seconds"],
                e["analyst"], e["notes"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    print(f"  Inserted {inserted} rows via direct SQLite.")


def insert_entries_logger(entries: list[dict], db_path: pathlib.Path) -> None:
    logger = AttackLogger(db_path)
    inserted = 0
    for e in entries:
        import json
        try:
            e2 = dict(e)
            # AttackLogger expects evidence as dict
            if isinstance(e2["evidence"], str):
                e2["evidence"] = json.loads(e2["evidence"])
            logger.log_attack(**e2)
            inserted += 1
        except Exception as ex:
            pass
    print(f"  Inserted {inserted} rows via AttackLogger.")


def print_summary(db_path: pathlib.Path) -> None:
    import json
    conn = sqlite3.connect(db_path)
    total = conn.execute("SELECT COUNT(*) FROM attack_logs").fetchone()[0]
    layers_covered = conn.execute("SELECT COUNT(DISTINCT layer_id) FROM attack_logs").fetchone()[0]

    sev = dict(conn.execute(
        "SELECT severity, COUNT(*) FROM attack_logs GROUP BY severity"
    ).fetchall())

    statuses = dict(conn.execute(
        "SELECT status, COUNT(*) FROM attack_logs GROUP BY status"
    ).fetchall())

    detected = sum(v for k, v in statuses.items() if k in ("DETECTED", "BLOCKED", "PARTIAL"))
    detection_rate = round(detected / total * 100, 1) if total else 0.0

    pqc_prevents = conn.execute(
        "SELECT COUNT(*) FROM attack_logs WHERE pqc_result LIKE 'PQC PREVENTS%'"
    ).fetchone()[0]
    pqc_pct = round(pqc_prevents / total * 100, 1) if total else 0.0

    conn.close()

    db_size_kb = round(os.path.getsize(db_path) / 1024, 0)

    print("\n=== Attack DB Population Complete ===")
    print(f"  Total entries: {total}")
    print(f"  Layers covered: {layers_covered}/29")
    print(f"  Severity: Critical={sev.get('CRITICAL',0)}, High={sev.get('HIGH',0)}, "
          f"Medium={sev.get('MEDIUM',0)}, Low={sev.get('LOW',0)}")
    print(f"  Detection rate: {detection_rate}%")
    print(f"  PQC prevents: {pqc_pct}% of attacks")
    print(f"  DB path: {db_path}")
    print(f"  DB size: {db_size_kb} KB")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TARGET = 600
    print(f"Generating {TARGET} attack log entries across 29 layers...")
    entries = generate_entries(n=TARGET, seed=42)
    print(f"  Generated {len(entries)} entries.")

    if _USE_LOGGER:
        insert_entries_logger(entries, DB_PATH)
    else:
        insert_entries_direct(entries, DB_PATH)

    print_summary(DB_PATH)
