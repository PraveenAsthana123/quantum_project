"""
attack_logger.py — Per-Layer Attack Logging System
Tracks every attack across all 29 security layers using SQLite.
"""

import sqlite3
import json
import time
import hashlib
import pathlib
import random
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = pathlib.Path(__file__).parent.parent / "results" / "attack_logs.db"


@dataclass
class AttackLog:
    log_id: str           # SHA256[:16] of timestamp+layer+attack
    timestamp: str        # ISO 8601
    layer_id: str         # L01–L29
    layer_name: str
    attack_name: str
    cve: str              # CVE ID or "N/A"
    tool_used: str
    mitre_technique: str  # T1xxx.xxx
    source_system: str    # S1/S2/S3/S4
    target_system: str
    severity: str         # CRITICAL/HIGH/MEDIUM/LOW
    status: str           # ATTEMPTED/BLOCKED/SUCCESS/PARTIAL/DETECTED/SIMULATED/ONGOING
    classical_result: str
    pqc_result: str
    evidence: dict        # {"pcap": "...", "hash": "...", "log_extract": "..."}
    detection_method: str
    response_action: str
    ttd_seconds: float    # Time To Detect  (-1 = N/A)
    ttr_seconds: float    # Time To Respond (-1 = N/A)
    analyst: str          # SOC-L1/SOC-L2/AUTOMATED
    notes: str


# ─── AttackLogger ─────────────────────────────────────────────────────────────

class AttackLogger:
    def __init__(self, db_path: pathlib.Path = DB_PATH):
        self.db_path = pathlib.Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── DB bootstrap ──────────────────────────────────────────────────────────

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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
                    evidence         TEXT,  -- JSON
                    detection_method TEXT,
                    response_action  TEXT,
                    ttd_seconds      REAL DEFAULT -1,
                    ttr_seconds      REAL DEFAULT -1,
                    analyst          TEXT,
                    notes            TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_layer   ON attack_logs(layer_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts      ON attack_logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON attack_logs(severity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status  ON attack_logs(status)")
            conn.commit()

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_id(timestamp: str, layer_id: str, attack_name: str) -> str:
        raw = f"{timestamp}{layer_id}{attack_name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _row_to_log(row: tuple) -> AttackLog:
        (log_id, timestamp, layer_id, layer_name, attack_name, cve,
         tool_used, mitre_technique, source_system, target_system,
         severity, status, classical_result, pqc_result, evidence_json,
         detection_method, response_action, ttd_seconds, ttr_seconds,
         analyst, notes) = row
        return AttackLog(
            log_id=log_id, timestamp=timestamp, layer_id=layer_id,
            layer_name=layer_name, attack_name=attack_name, cve=cve,
            tool_used=tool_used, mitre_technique=mitre_technique,
            source_system=source_system, target_system=target_system,
            severity=severity, status=status,
            classical_result=classical_result, pqc_result=pqc_result,
            evidence=json.loads(evidence_json or "{}"),
            detection_method=detection_method, response_action=response_action,
            ttd_seconds=ttd_seconds if ttd_seconds is not None else -1,
            ttr_seconds=ttr_seconds if ttr_seconds is not None else -1,
            analyst=analyst, notes=notes,
        )

    # ── public API ────────────────────────────────────────────────────────────

    def log_attack(self, **kwargs) -> AttackLog:
        ts = kwargs.get("timestamp", datetime.utcnow().isoformat())
        layer_id = kwargs["layer_id"]
        attack_name = kwargs["attack_name"]
        log_id = kwargs.get("log_id") or self._make_id(ts, layer_id, attack_name)

        entry = AttackLog(
            log_id=log_id,
            timestamp=ts,
            layer_id=layer_id,
            layer_name=kwargs.get("layer_name", ""),
            attack_name=attack_name,
            cve=kwargs.get("cve", "N/A"),
            tool_used=kwargs.get("tool_used", ""),
            mitre_technique=kwargs.get("mitre_technique", ""),
            source_system=kwargs.get("source_system", ""),
            target_system=kwargs.get("target_system", ""),
            severity=kwargs.get("severity", "MEDIUM"),
            status=kwargs.get("status", "ATTEMPTED"),
            classical_result=kwargs.get("classical_result", ""),
            pqc_result=kwargs.get("pqc_result", ""),
            evidence=kwargs.get("evidence", {}),
            detection_method=kwargs.get("detection_method", ""),
            response_action=kwargs.get("response_action", ""),
            ttd_seconds=kwargs.get("ttd_seconds", -1),
            ttr_seconds=kwargs.get("ttr_seconds", -1),
            analyst=kwargs.get("analyst", "AUTOMATED"),
            notes=kwargs.get("notes", ""),
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO attack_logs VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry.log_id, entry.timestamp, entry.layer_id, entry.layer_name,
                entry.attack_name, entry.cve, entry.tool_used, entry.mitre_technique,
                entry.source_system, entry.target_system, entry.severity, entry.status,
                entry.classical_result, entry.pqc_result,
                json.dumps(entry.evidence),
                entry.detection_method, entry.response_action,
                entry.ttd_seconds, entry.ttr_seconds,
                entry.analyst, entry.notes,
            ))
            conn.commit()
        return entry

    def get_layer_logs(self, layer_id: str) -> list[AttackLog]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM attack_logs WHERE layer_id=? ORDER BY timestamp DESC",
                (layer_id,)
            ).fetchall()
        return [self._row_to_log(r) for r in rows]

    def get_recent_logs(self, limit: int = 50) -> list[AttackLog]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM attack_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [self._row_to_log(r) for r in rows]

    def get_attack_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM attack_logs").fetchone()[0]

            by_severity = dict(conn.execute(
                "SELECT severity, COUNT(*) FROM attack_logs GROUP BY severity"
            ).fetchall())

            by_status = dict(conn.execute(
                "SELECT status, COUNT(*) FROM attack_logs GROUP BY status"
            ).fetchall())

            by_layer = dict(conn.execute(
                "SELECT layer_id, COUNT(*) FROM attack_logs GROUP BY layer_id ORDER BY COUNT(*) DESC"
            ).fetchall())

            by_source = dict(conn.execute(
                "SELECT source_system, COUNT(*) FROM attack_logs GROUP BY source_system"
            ).fetchall())

            # Attacks per hour over last 24h
            cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            recent_count = conn.execute(
                "SELECT COUNT(*) FROM attack_logs WHERE timestamp >= ?", (cutoff,)
            ).fetchone()[0]
            attacks_per_hour = round(recent_count / 24, 2)

            # Detection rate = (DETECTED + BLOCKED) / total
            detected = by_status.get("DETECTED", 0) + by_status.get("BLOCKED", 0)
            detection_rate = round(detected / total * 100, 1) if total else 0.0

            # Block rate = BLOCKED / total
            block_rate = round(by_status.get("BLOCKED", 0) / total * 100, 1) if total else 0.0

        return {
            "total_attacks": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "by_layer": by_layer,
            "by_source": by_source,
            "attacks_per_hour": attacks_per_hour,
            "detection_rate": detection_rate,
            "block_rate": block_rate,
        }

    def get_layer_timeline(self, layer_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT timestamp, attack_name, severity, status, ttd_seconds
                   FROM attack_logs WHERE layer_id=? ORDER BY timestamp ASC""",
                (layer_id,)
            ).fetchall()
        return [
            {"timestamp": r[0], "attack_name": r[1], "severity": r[2],
             "status": r[3], "ttd_seconds": r[4]}
            for r in rows
        ]

    def search_logs(
        self,
        layer_id: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        attack_name: Optional[str] = None,
        cve: Optional[str] = None,
    ) -> list[AttackLog]:
        clauses, params = [], []
        if layer_id:
            clauses.append("layer_id = ?"); params.append(layer_id)
        if severity:
            clauses.append("severity = ?"); params.append(severity)
        if status:
            clauses.append("status = ?"); params.append(status)
        if attack_name:
            clauses.append("attack_name LIKE ?"); params.append(f"%{attack_name}%")
        if cve:
            clauses.append("cve = ?"); params.append(cve)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM attack_logs {where} ORDER BY timestamp DESC"

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_log(r) for r in rows]

    def generate_layer_report(self, layer_id: str) -> dict:
        logs = self.get_layer_logs(layer_id)
        if not logs:
            return {"layer_id": layer_id, "error": "No logs found"}

        severity_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        evidence_list = []
        ttd_vals, ttr_vals = [], []

        for log in logs:
            severity_counts[log.severity] = severity_counts.get(log.severity, 0) + 1
            status_counts[log.status] = status_counts.get(log.status, 0) + 1
            if log.evidence:
                evidence_list.append({"attack": log.attack_name, "evidence": log.evidence})
            if log.ttd_seconds > 0:
                ttd_vals.append(log.ttd_seconds)
            if log.ttr_seconds > 0:
                ttr_vals.append(log.ttr_seconds)

        detected = status_counts.get("DETECTED", 0) + status_counts.get("BLOCKED", 0)
        detection_rate = round(detected / len(logs) * 100, 1) if logs else 0.0

        return {
            "layer_id": layer_id,
            "layer_name": logs[0].layer_name,
            "total_attacks": len(logs),
            "severity_breakdown": severity_counts,
            "status_breakdown": status_counts,
            "timeline": self.get_layer_timeline(layer_id),
            "evidence_list": evidence_list,
            "detection_rate": detection_rate,
            "avg_ttd_seconds": round(sum(ttd_vals) / len(ttd_vals), 2) if ttd_vals else -1,
            "avg_ttr_seconds": round(sum(ttr_vals) / len(ttr_vals), 2) if ttr_vals else -1,
        }

    def export_json(self, layer_id: Optional[str] = None) -> str:
        logs = self.get_layer_logs(layer_id) if layer_id else self.get_recent_logs(limit=9999)
        return json.dumps([asdict(log) for log in logs], indent=2)

    # ── Simulation ────────────────────────────────────────────────────────────

    def simulate_attack_session(self):
        """Populate the DB with realistic attack entries across all 29 layers."""

        now = datetime.utcnow()

        def ts(days_ago=0, hours_ago=0, minutes_ago=0) -> str:
            return (now - timedelta(days=days_ago, hours=hours_ago,
                                    minutes=minutes_ago)).isoformat()

        # ── Pre-defined key-layer attacks ─────────────────────────────────────

        entries = [

            # L03 IPsec
            dict(timestamp=ts(days_ago=0, hours_ago=2), layer_id="L03",
                 layer_name="IPsec/VPN Layer", attack_name="IKEv2 Aggressive Mode",
                 cve="CVE-2018-7182", tool_used="ike-scan", mitre_technique="T1190",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="DETECTED",
                 classical_result="IKEv2 aggressive mode probe responded with hash",
                 pqc_result="PQC-IKE rejected non-PQC cipher suite",
                 evidence={"pcap": "ike_aggressive_2025.pcap", "hash": "a3f8b291c4d5e6f7",
                           "log_extract": "IKE_SA_INIT aggressive mode detected from 10.0.0.5"},
                 detection_method="IDS signature IKE-AGGRESSIVE-001",
                 response_action="Blocked source IP; alert SOC-L1",
                 ttd_seconds=45, ttr_seconds=120, analyst="SOC-L1",
                 notes="IKEv2 aggressive mode exposes hash to offline crack"),

            dict(timestamp=ts(days_ago=0, hours_ago=2, minutes_ago=5), layer_id="L03",
                 layer_name="IPsec/VPN Layer", attack_name="DH-2048 Quantum Simulation",
                 cve="N/A", tool_used="Shor's-sim", mitre_technique="T1557",
                 source_system="S2", target_system="S3 Classical",
                 severity="CRITICAL", status="DETECTED_QUANTUM",
                 classical_result="VULNERABLE: DH-2048 breakable by Shor's algorithm",
                 pqc_result="PROTECTED: ML-KEM-1024 IKE extension active",
                 evidence={"simulation": "shor_dh2048_sim.json",
                           "hash": "b7c2d391e5f6a8b9",
                           "log_extract": "Quantum threat model: DH-2048 estimated break ~7min on 4000-qubit QPU"},
                 detection_method="Quantum Threat Intelligence feed",
                 response_action="Migration to PQC IKE completed on S4",
                 ttd_seconds=0, ttr_seconds=0, analyst="AUTOMATED",
                 notes="Simulation only — no live quantum attacker; marks future risk"),

            # L04 TLS
            dict(timestamp=ts(days_ago=1, hours_ago=4), layer_id="L04",
                 layer_name="TLS/HTTPS Layer", attack_name="Heartbleed",
                 cve="CVE-2014-0160", tool_used="heartbleed-poc",
                 mitre_technique="T1190",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="BLOCKED",
                 classical_result="Patched: OpenSSL ≥ 1.0.1g; heartbeat extension rejected",
                 pqc_result="N/A — patch-level control",
                 evidence={"pcap": "heartbleed_probe_443.pcap",
                           "hash": "c9d1e4f2a3b5c7d8",
                           "log_extract": "TCP SYN port 443 from 192.168.1.50; OpenSSL version 3.1.2 (not vulnerable)"},
                 detection_method="WAF rule CVE-2014-0160; IDS sig",
                 response_action="Request dropped; source IP logged",
                 ttd_seconds=2, ttr_seconds=0.1, analyst="AUTOMATED",
                 notes="Heartbeat extension disabled at compile time"),

            dict(timestamp=ts(days_ago=1, hours_ago=4, minutes_ago=10), layer_id="L04",
                 layer_name="TLS/HTTPS Layer", attack_name="ROBOT Attack",
                 cve="CVE-2017-13099", tool_used="robot-detect",
                 mitre_technique="T1557.002",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="BLOCKED",
                 classical_result="ECDHE-only: RSA key exchange disabled; PKCS#1v1.5 padding rejected",
                 pqc_result="ML-KEM ephemeral exchange; RSA padding irrelevant",
                 evidence={"pcap": "robot_probe_tls.pcap",
                           "hash": "d4e5f6a7b8c9d0e1",
                           "log_extract": "RSA PKCS1v1.5 CKE probe rejected; ECDHE handshake enforced"},
                 detection_method="TLS policy enforcement; Zeek alert",
                 response_action="Handshake aborted; alert queued",
                 ttd_seconds=0.3, ttr_seconds=0.05, analyst="AUTOMATED",
                 notes="ECDHE cipher-suite enforcement prevents oracle"),

            dict(timestamp=ts(days_ago=0, hours_ago=1), layer_id="L04",
                 layer_name="TLS/HTTPS Layer", attack_name="HNDL Recording",
                 cve="N/A", tool_used="passive-capture",
                 mitre_technique="T1040",
                 source_system="S2", target_system="S3 Classical",
                 severity="CRITICAL", status="ONGOING",
                 classical_result="847,293 encrypted TLS packets captured; decryptable when CRQC available (~2031)",
                 pqc_result="S4 traffic: ML-KEM-1024 ciphertext — HNDL-resistant",
                 evidence={"pcap": "hndl_capture_2025-10-01.pcap",
                           "hash": "e6f7a8b9c0d1e2f3",
                           "log_extract": "Passive tap on 185.220.101.45; 847293 pkts to S3 endpoints"},
                 detection_method="Network tap anomaly (high-volume passive capture)",
                 response_action="S3→S4 migration accelerated; forward secrecy audit",
                 ttd_seconds=-1, ttr_seconds=-1, analyst="SOC-L2",
                 notes="Harvest-now-decrypt-later — passive capture undetectable until QPU exists"),

            # L06 PKI
            dict(timestamp=ts(days_ago=2, hours_ago=6), layer_id="L06",
                 layer_name="PKI / Certificate Authority", attack_name="Certificate Spoofing",
                 cve="CVE-2020-0601", tool_used="curveball-poc",
                 mitre_technique="T1553.004",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="DETECTED",
                 classical_result="CurveBall exploit attempted; ECC curve parameters validated — patch applied",
                 pqc_result="Dilithium-3 cert chain unaffected by EC curve manipulation",
                 evidence={"cert": "fake_ca_cert.pem",
                           "hash": "f7a8b9c0d1e2f3a4",
                           "log_extract": "Certificate chain validation fail: explicit EC params mismatch"},
                 detection_method="CT log monitor; cert-lint alert",
                 response_action="Rogue cert revoked; CAA record tightened",
                 ttd_seconds=120, ttr_seconds=600, analyst="SOC-L1",
                 notes="CVE-2020-0601 patched; CT transparency monitoring active"),

            dict(timestamp=ts(days_ago=0, hours_ago=3), layer_id="L06",
                 layer_name="PKI / Certificate Authority", attack_name="Quantum CA Attack",
                 cve="N/A", tool_used="Shor's-sim",
                 mitre_technique="T1588.003",
                 source_system="S2", target_system="S3 Classical",
                 severity="CRITICAL", status="SIMULATED",
                 classical_result="VULNERABLE: RSA-2048 CA key factored by Shor's in simulation",
                 pqc_result="PROTECTED: SLH-DSA root CA deployed on S4; Shor's ineffective",
                 evidence={"simulation": "shor_rsa2048_ca_sim.json",
                           "hash": "a8b9c0d1e2f3a4b5",
                           "log_extract": "Simulation: RSA-2048 CA private key recovered in 4.2 min on 4096-qubit model"},
                 detection_method="Future threat model",
                 response_action="PQC CA migration in progress; root cross-signed with Dilithium",
                 ttd_seconds=0, ttr_seconds=0, analyst="AUTOMATED",
                 notes="Future threat — simulation only"),

            # L08 JWT
            dict(timestamp=ts(days_ago=0, hours_ago=0, minutes_ago=15), layer_id="L08",
                 layer_name="JWT / Token Auth", attack_name="Algorithm Confusion RS256→HS256",
                 cve="CVE-2015-9235", tool_used="jwt_tool.py",
                 mitre_technique="T1550.001",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="SUCCESS",
                 classical_result="S3 server accepted HMAC-signed JWT using public key as secret",
                 pqc_result="S4 server enforces Dilithium-3; alg field validated strictly",
                 evidence={"token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiJ9.xxx",
                           "hash": "b9c0d1e2f3a4b5c6",
                           "log_extract": "JWT accepted on S3: alg=HS256, signed with RSA public key"},
                 detection_method="MISSED by S3 — no alg whitelist",
                 response_action="S3 patched to whitelist RS256 only; emergency rollout",
                 ttd_seconds=15120, ttr_seconds=3600, analyst="SOC-L2",
                 notes="4.2h TTD — detected during routine log review, not real-time"),

            dict(timestamp=ts(days_ago=0, hours_ago=0, minutes_ago=14), layer_id="L08",
                 layer_name="JWT / Token Auth", attack_name="Algorithm Confusion RS256→HS256",
                 cve="CVE-2015-9235", tool_used="jwt_tool.py",
                 mitre_technique="T1550.001",
                 source_system="S1", target_system="S4 PQC",
                 severity="CRITICAL", status="BLOCKED",
                 classical_result="N/A — S4 not using RSA",
                 pqc_result="S4 blocked: Dilithium-3 verification failed on HMAC token",
                 evidence={"log_extract": "S4 rejected JWT: expected Dilithium-3 signature, got HMAC-SHA256"},
                 detection_method="Algorithm whitelist enforcement",
                 response_action="Request rejected; attacker IP logged",
                 ttd_seconds=0.1, ttr_seconds=0.05, analyst="AUTOMATED",
                 notes="PQC strict alg validation prevents confusion attack"),

            dict(timestamp=ts(days_ago=0, hours_ago=5), layer_id="L08",
                 layer_name="JWT / Token Auth", attack_name="JWT alg:none",
                 cve="CVE-2015-9235", tool_used="jwt_tool.py",
                 mitre_technique="T1550.001",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="BLOCKED",
                 classical_result="Server enforces RS256; alg=none rejected at middleware",
                 pqc_result="S4 enforces Dilithium-3; alg=none rejected",
                 evidence={"token": "eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.",
                           "hash": "c0d1e2f3a4b5c6d7",
                           "log_extract": "JWT validation error: unsigned token rejected (alg=none)"},
                 detection_method="JWT middleware alg whitelist",
                 response_action="Request rejected 400; rate-limit triggered",
                 ttd_seconds=0.1, ttr_seconds=0.05, analyst="AUTOMATED",
                 notes="alg whitelist ['RS256'] enforced at gateway"),

            dict(timestamp=ts(days_ago=3, hours_ago=2), layer_id="L08",
                 layer_name="JWT / Token Auth", attack_name="JWT Secret Brute Force",
                 cve="N/A", tool_used="hashcat",
                 mitre_technique="T1110.002",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="PARTIAL",
                 classical_result="Weak test secret 'secret123' cracked in lab in 3600s",
                 pqc_result="Dilithium-3 private key: brute force infeasible (lattice)",
                 evidence={"wordlist": "rockyou-jwt.txt",
                           "hash": "d1e2f3a4b5c6d7e8",
                           "log_extract": "hashcat cracked HMAC-SHA256 secret: 'secret123' (3600s, RTX3090)"},
                 detection_method="Lab finding — not detected in production",
                 response_action="Production secret rotated to 256-bit random; lab secret removed",
                 ttd_seconds=3600, ttr_seconds=600, analyst="SOC-L2",
                 notes="Test environment only — production uses HSM-backed key"),

            dict(timestamp=ts(days_ago=1, hours_ago=7), layer_id="L08",
                 layer_name="JWT / Token Auth", attack_name="KID Injection",
                 cve="N/A", tool_used="jwt_tool.py",
                 mitre_technique="T1190",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="BLOCKED",
                 classical_result="KID parameter sanitised; path traversal rejected",
                 pqc_result="S4: KID validation uses JWKS URI — no FS path exposure",
                 evidence={"payload": '{"kid": "../../etc/passwd"}',
                           "hash": "e2f3a4b5c6d7e8f9",
                           "log_extract": "JWT KID path traversal detected and blocked at parser"},
                 detection_method="Input validation; WAF rule",
                 response_action="Request blocked 400; IP added to watchlist",
                 ttd_seconds=0.5, ttr_seconds=0.1, analyst="AUTOMATED",
                 notes="KID allowlist implemented post-finding"),

            # L10 SSH
            dict(timestamp=ts(days_ago=4, hours_ago=3), layer_id="L10",
                 layer_name="SSH Layer", attack_name="OpenSSH Agent Forwarding RCE",
                 cve="CVE-2023-38408", tool_used="ssh-agent-exploit",
                 mitre_technique="T1021.004",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="BLOCKED",
                 classical_result="Agent forwarding disabled in sshd_config; exploit path unavailable",
                 pqc_result="N/A — config-level control",
                 evidence={"config": "AllowAgentForwarding no",
                           "hash": "f3a4b5c6d7e8f9a0",
                           "log_extract": "SSH agent forward request rejected: AllowAgentForwarding=no"},
                 detection_method="SSH daemon policy enforcement",
                 response_action="Connection closed; alert generated",
                 ttd_seconds=5, ttr_seconds=1, analyst="AUTOMATED",
                 notes="Disabled by hardening baseline"),

            dict(timestamp=ts(days_ago=2, hours_ago=5), layer_id="L10",
                 layer_name="SSH Layer", attack_name="Terrapin Attack",
                 cve="CVE-2023-48795", tool_used="terrapin-scanner",
                 mitre_technique="T1557",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="DETECTED",
                 classical_result="ChaCha20-Poly1305 sequence number manipulation detected",
                 pqc_result="PQC SSH (OpenSSH 9.x + ML-KEM): strict-kex-ext enabled, Terrapin blocked",
                 evidence={"pcap": "terrapin_probe.pcap",
                           "hash": "a4b5c6d7e8f9a0b1",
                           "log_extract": "SSH negotiation: chacha20-poly1305 strip attempt; strict-kex enforced"},
                 detection_method="SSH strict mode; IDS signature CVE-2023-48795",
                 response_action="Session terminated; patch applied (OpenSSH 9.6)",
                 ttd_seconds=8, ttr_seconds=30, analyst="SOC-L1",
                 notes="strict-kex extension mitigates; all hosts patched"),

            dict(timestamp=ts(days_ago=0, hours_ago=6), layer_id="L10",
                 layer_name="SSH Layer", attack_name="SSH Brute Force",
                 cve="N/A", tool_used="hydra",
                 mitre_technique="T1110.003",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="BLOCKED",
                 classical_result="47 failed attempts; fail2ban blocked after 5 failures",
                 pqc_result="S4 SSH: key-only auth; password auth disabled",
                 evidence={"log_extract": "47 failed SSH login attempts from 198.51.100.23; fail2ban rule triggered",
                           "hash": "b5c6d7e8f9a0b1c2"},
                 detection_method="fail2ban; SIEM correlation",
                 response_action="IP blocked 24h; alert SOC-L1",
                 ttd_seconds=15, ttr_seconds=5, analyst="AUTOMATED",
                 notes="PasswordAuthentication no on S4"),

            # L14 KMS/Vault
            dict(timestamp=ts(days_ago=1, hours_ago=2), layer_id="L14",
                 layer_name="KMS / Vault Layer", attack_name="Vault Token Theft",
                 cve="CVE-2023-2197", tool_used="custom-vault-exploit",
                 mitre_technique="T1552.001",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="DETECTED",
                 classical_result="Token stolen from env var; Vault audit log triggered alert",
                 pqc_result="S4 Vault: short-TTL PQC-signed tokens; replay rejected",
                 evidence={"token": "s.XXXXXXXXXXXX",
                           "hash": "c6d7e8f9a0b1c2d3",
                           "log_extract": "Vault token s.XXXX used from unexpected IP 203.0.113.7"},
                 detection_method="Vault audit backend; geo-anomaly alert",
                 response_action="Token revoked; env var audited; secret rotation triggered",
                 ttd_seconds=30, ttr_seconds=60, analyst="SOC-L2",
                 notes="Token in env var — migrated to Vault agent injection"),

            dict(timestamp=ts(days_ago=0, hours_ago=4), layer_id="L14",
                 layer_name="KMS / Vault Layer", attack_name="RSA Key Export Quantum",
                 cve="N/A", tool_used="Shor's-sim",
                 mitre_technique="T1552.004",
                 source_system="S2", target_system="S3 Classical",
                 severity="CRITICAL", status="SIMULATED",
                 classical_result="VULNERABLE: RSA-4096 KMS master key recoverable by Shor's",
                 pqc_result="PROTECTED: ML-KEM-1024 wrapping key; Shor's ineffective on lattice",
                 evidence={"simulation": "shor_rsa4096_kms.json",
                           "hash": "d7e8f9a0b1c2d3e4",
                           "log_extract": "Simulation: RSA-4096 KMS key factored in 8.7 min on 5000-qubit model"},
                 detection_method="Quantum threat model",
                 response_action="KMS migration to ML-KEM scheduled Q1-2026",
                 ttd_seconds=0, ttr_seconds=0, analyst="AUTOMATED",
                 notes="Future threat — crypto-agility plan in place"),

            # L15 IAM
            dict(timestamp=ts(days_ago=5, hours_ago=1), layer_id="L15",
                 layer_name="IAM / AuthN-AuthZ", attack_name="Golden Ticket Attack",
                 cve="N/A", tool_used="mimikatz",
                 mitre_technique="T1558.001",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="SUCCESS",
                 classical_result="krbtgt NTLM hash obtained; forged Kerberos TGT valid 10y",
                 pqc_result="S4 IAM: Dilithium-3 signed tokens; NTLM hash irrelevant",
                 evidence={"dump": "krbtgt_hash.txt",
                           "hash": "e8f9a0b1c2d3e4f5",
                           "log_extract": "Unusual TGT lifetime 10y detected; SOC-L1 missed initial alert"},
                 detection_method="SIEM rule: TGT lifetime > 8h (triggered 30m late)",
                 response_action="krbtgt rotated twice; all tickets invalidated; EDR sweep",
                 ttd_seconds=1800, ttr_seconds=3600, analyst="SOC-L2",
                 notes="SOC-L1 missed initial alert — escalated to SOC-L2 after 30m"),

            dict(timestamp=ts(days_ago=3, hours_ago=8), layer_id="L15",
                 layer_name="IAM / AuthN-AuthZ", attack_name="SAML Signature Wrapping",
                 cve="CVE-2018-0486", tool_used="saml-raider",
                 mitre_technique="T1606.002",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="BLOCKED",
                 classical_result="XML signature wrapping rejected; schema validation enforced",
                 pqc_result="S4 uses OIDC with Dilithium-3 JWTs; SAML not in attack surface",
                 evidence={"saml": "wrapped_saml_assertion.xml",
                           "hash": "f9a0b1c2d3e4f5a6",
                           "log_extract": "SAML signature wrapping detected: assertion ID mismatch"},
                 detection_method="XML schema strict validation; SAML parser hardening",
                 response_action="Request rejected 403; alert AUTOMATED",
                 ttd_seconds=0.2, ttr_seconds=0.05, analyst="AUTOMATED",
                 notes="SAML schema-strict mode prevents wrapping"),

            dict(timestamp=ts(days_ago=1, hours_ago=9), layer_id="L15",
                 layer_name="IAM / AuthN-AuthZ", attack_name="Pass-the-Hash",
                 cve="N/A", tool_used="mimikatz",
                 mitre_technique="T1550.002",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="DETECTED",
                 classical_result="NTLM hash used for lateral movement; EDR detected within 12s",
                 pqc_result="S4: certificate-based auth only; NTLM disabled",
                 evidence={"log_extract": "EDR alert: pass-the-hash lateral movement from 10.0.1.5 to 10.0.1.8",
                           "hash": "a0b1c2d3e4f5a6b7"},
                 detection_method="EDR behavioral detection",
                 response_action="Host quarantined; credential reset; incident opened",
                 ttd_seconds=12, ttr_seconds=180, analyst="SOC-L1",
                 notes="EDR behavioral heuristics caught PtH pattern"),

            # L18 Blockchain
            dict(timestamp=ts(days_ago=6, hours_ago=2), layer_id="L18",
                 layer_name="Blockchain / DLT Layer", attack_name="ECDSA k-value Reuse",
                 cve="N/A", tool_used="lattice-attack",
                 mitre_technique="T1552.004",
                 source_system="S2", target_system="S3 Classical",
                 severity="CRITICAL", status="SUCCESS",
                 classical_result="Private key recovered from two tx with same k-nonce; lab wallet drained",
                 pqc_result="S4 Blockchain: Dilithium-3 signatures; deterministic nonce per RFC6979",
                 evidence={"tx1": "0xabc123", "tx2": "0xdef456",
                           "hash": "b1c2d3e4f5a6b7c8",
                           "log_extract": "Lattice attack: private key d extracted from k-reuse on tx 0xabc123 and 0xdef456"},
                 detection_method="Post-mortem analysis (lab)",
                 response_action="Lab wallet decommissioned; prod uses deterministic k",
                 ttd_seconds=-1, ttr_seconds=-1, analyst="SOC-L2",
                 notes="Production uses RFC6979 deterministic k — this was lab wallet"),

            dict(timestamp=ts(days_ago=0, hours_ago=3), layer_id="L18",
                 layer_name="Blockchain / DLT Layer", attack_name="Quantum Wallet Attack",
                 cve="N/A", tool_used="Shor's-sim",
                 mitre_technique="T1552.004",
                 source_system="S2", target_system="S3 Classical",
                 severity="CRITICAL", status="SIMULATED",
                 classical_result="VULNERABLE: ECDSA secp256k1 public key → private key via Shor's",
                 pqc_result="PROTECTED: CRYSTALS-Dilithium wallet; quantum-safe",
                 evidence={"simulation": "shor_ecdsa_wallet.json",
                           "hash": "c2d3e4f5a6b7c8d9",
                           "log_extract": "Sim: secp256k1 private key recovered in 6.1 min; $2.3M in wallet at risk"},
                 detection_method="Quantum threat model",
                 response_action="Migration to PQC wallet underway; funds transferred to Dilithium address",
                 ttd_seconds=0, ttr_seconds=0, analyst="AUTOMATED",
                 notes="Estimated $2.3M at risk in classical wallet addresses"),

            # L22 Firmware
            dict(timestamp=ts(days_ago=7, hours_ago=5), layer_id="L22",
                 layer_name="Firmware / Boot Security", attack_name="BootHole",
                 cve="CVE-2020-10713", tool_used="boothole-poc",
                 mitre_technique="T1542.001",
                 source_system="S1", target_system="S3 Classical",
                 severity="CRITICAL", status="BLOCKED",
                 classical_result="Patched GRUB2; dbx updated with BootHole revocation certs",
                 pqc_result="S4: PQC Secure Boot with Dilithium-3 shim signature",
                 evidence={"grub_ver": "2.06-3", "hash": "d3e4f5a6b7c8d9e0",
                           "log_extract": "Secure Boot dbx check blocked known-bad GRUB2 binary hash"},
                 detection_method="UEFI Secure Boot dbx revocation",
                 response_action="GRUB2 updated; Secure Boot enforced; SOC-L2 notified",
                 ttd_seconds=180, ttr_seconds=3600, analyst="SOC-L2",
                 notes="All images re-signed; dbx deployed via BIOS update"),

            dict(timestamp=ts(days_ago=2, hours_ago=7), layer_id="L22",
                 layer_name="Firmware / Boot Security", attack_name="TPM PCR Replay",
                 cve="N/A", tool_used="tpm-replay-tool",
                 mitre_technique="T1542.005",
                 source_system="S1", target_system="S3 Classical",
                 severity="HIGH", status="DETECTED",
                 classical_result="TPM PCR snapshot replayed; TPM quote verification failed",
                 pqc_result="S4: TPM2 with EK cert + Dilithium attestation; replay rejected",
                 evidence={"pcr_log": "pcr_replay.bin",
                           "hash": "e4f5a6b7c8d9e0f1",
                           "log_extract": "TPM attestation challenge-response failed: nonce mismatch"},
                 detection_method="Remote attestation challenge-response",
                 response_action="Host quarantined for firmware audit; TPM cleared and re-enrolled",
                 ttd_seconds=240, ttr_seconds=7200, analyst="SOC-L2",
                 notes="Challenge-nonce prevents PCR replay"),
        ]

        # ── Generic attacks for remaining layers ──────────────────────────────

        remaining_layers = [
            ("L01", "Network Transport"), ("L02", "DNS / DNSSEC"),
            ("L05", "QUIC / HTTP3"), ("L07", "mTLS / Service Mesh"),
            ("L09", "API Gateway"), ("L11", "Secret Management"),
            ("L12", "Code Signing"), ("L13", "VPN / WireGuard"),
            ("L16", "Container Security"), ("L17", "Supply Chain"),
            ("L19", "Cloud IAM"), ("L20", "Database Encryption"),
            ("L21", "Logging / SIEM"), ("L23", "DevSecOps Pipeline"),
            ("L24", "Endpoint / EDR"), ("L25", "Zero Trust"),
            ("L26", "AI Model Security"), ("L27", "Quantum Channel"),
            ("L28", "QKD Layer"), ("L29", "Post-Quantum Migration"),
        ]

        generic_attacks = [
            ("Recon Scan", "T1595", "nmap", "S1", "MEDIUM", "DETECTED",
             "N/A", 30, 60),
            ("Protocol Downgrade", "T1557", "custom", "S1", "HIGH", "BLOCKED",
             "CVE-2019-14899", 5, 10),
            ("Quantum Simulation", "T1557", "Shor's-sim", "S2", "CRITICAL", "SIMULATED",
             "N/A", 0, 0),
            ("Credential Stuffing", "T1110.004", "credstuff-tool", "S1", "HIGH", "BLOCKED",
             "N/A", 10, 15),
            ("Supply Chain Inject", "T1195", "custom", "S1", "CRITICAL", "DETECTED",
             "N/A", 120, 300),
        ]

        rng = random.Random(42)  # deterministic for reproducibility
        for layer_id, layer_name in remaining_layers:
            num_attacks = rng.randint(3, 5)
            selected = rng.sample(generic_attacks, min(num_attacks, len(generic_attacks)))
            for i, (atk_name, mitre, tool, src, sev, status, cve, ttd, ttr) in enumerate(selected):
                age_days = rng.uniform(0, 7)
                t = (now - timedelta(days=age_days)).isoformat()
                entries.append(dict(
                    timestamp=t, layer_id=layer_id, layer_name=layer_name,
                    attack_name=atk_name, cve=cve, tool_used=tool,
                    mitre_technique=mitre, source_system=src,
                    target_system="S3 Classical" if i % 2 == 0 else "S4 PQC",
                    severity=sev, status=status,
                    classical_result=f"{atk_name} attempted on {layer_name}",
                    pqc_result="PQC layer defended" if status == "BLOCKED" else "Monitoring",
                    evidence={"hash": hashlib.sha256(f"{layer_id}{atk_name}{i}".encode()).hexdigest()[:16],
                              "log_extract": f"{atk_name} event on {layer_name}"},
                    detection_method="IDS/SIEM", response_action="Alert generated",
                    ttd_seconds=float(ttd), ttr_seconds=float(ttr), analyst="AUTOMATED",
                    notes=f"Generated entry for {layer_name}",
                ))

        for e in entries:
            self.log_attack(**e)

        print(f"[simulate] Inserted {len(entries)} attack log entries across 29 layers.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  Quantum Security Attack Logger — Simulation Run")
    print("=" * 70)

    logger = AttackLogger()
    logger.simulate_attack_session()

    stats = logger.get_attack_stats()
    print("\n── OVERALL STATS ──────────────────────────────────────────────────")
    print(f"  Total logs       : {stats['total_attacks']}")
    print(f"  By severity      : {stats['by_severity']}")
    print(f"  By status        : {stats['by_status']}")
    print(f"  Detection rate   : {stats['detection_rate']}%")
    print(f"  Block rate       : {stats['block_rate']}%")
    print(f"  Attacks/hour     : {stats['attacks_per_hour']}")

    for lid in ("L04", "L08"):
        report = logger.generate_layer_report(lid)
        print(f"\n── LAYER REPORT: {lid} ({report.get('layer_name', '')}) ──")
        print(f"  Total attacks    : {report['total_attacks']}")
        print(f"  Severity         : {report['severity_breakdown']}")
        print(f"  Status           : {report['status_breakdown']}")
        print(f"  Detection rate   : {report['detection_rate']}%")
        print(f"  Avg TTD          : {report['avg_ttd_seconds']}s")
        print(f"  Avg TTR          : {report['avg_ttr_seconds']}s")

    print("\n── LAST 10 LOGS ───────────────────────────────────────────────────")
    for log in logger.get_recent_logs(limit=10):
        ttd_str = f"{log.ttd_seconds:.1f}s" if log.ttd_seconds > 0 else "—"
        print(f"  [{log.timestamp[:19]}] {log.layer_id} | {log.attack_name[:35]:<35} "
              f"| {log.severity:<8} | {log.status:<18} | TTD {ttd_str}")

    print(f"\n  DB: {DB_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
