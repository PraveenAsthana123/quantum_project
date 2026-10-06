"""
Attack Detection and Monitoring System
=======================================
Detectors for cryptographic attacks, HNDL, JWT anomalies, timing side-channels,
and AI attack patterns. Simulates a 24-hour traffic sample with embedded attacks.

Defensive Security Educational Lab — /mnt/deepa/quantum/qc-attack-lab/
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    detector: str
    severity: str       # CRITICAL / HIGH / MEDIUM / LOW
    description: str
    timestamp: float
    evidence: dict = field(default_factory=dict)
    mitre_technique: str = ""

    def display(self, indent: str = "  "):
        icon = {"CRITICAL": "[!!!]", "HIGH": "[!! ]", "MEDIUM": "[ ! ]", "LOW": "[   ]"}
        print(f"{indent}{icon.get(self.severity, '[   ]')} {self.severity:<9} "
              f"| {self.detector:<36} | {self.description[:60]}")
        for k, v in self.evidence.items():
            print(f"{indent}         └─ {k}: {v}")


@dataclass
class TrafficSample:
    """Represents one event/request in simulated traffic."""
    timestamp: float
    source_ip: str
    dest_ip: str
    protocol: str       # TLS / JWT / SSH / API
    payload_bytes: int
    operation: str      # e.g. "RSA_SIGN", "AES_ENC", "JWT_VERIFY"
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Individual Detectors
# ---------------------------------------------------------------------------

class TimingAnomalyDetector:
    """
    Detect timing side-channel patterns:
    unusually high variance in response times for the same operation.
    """

    NAME = "TimingAnomalyDetector"
    VARIANCE_THRESHOLD = 5.0    # ms²
    MIN_SAMPLES = 10

    def detect(self, traffic_sample: list[TrafficSample]) -> list[Alert]:
        alerts: list[Alert] = []
        # Group by operation type
        ops: dict[str, list[float]] = {}
        for ev in traffic_sample:
            rt = ev.extra.get("response_time_ms")
            if rt is not None:
                ops.setdefault(ev.operation, []).append(rt)

        for op, times in ops.items():
            if len(times) < self.MIN_SAMPLES:
                continue
            mean = sum(times) / len(times)
            variance = sum((t - mean) ** 2 for t in times) / len(times)
            if variance > self.VARIANCE_THRESHOLD:
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="HIGH",
                    description=f"High timing variance on {op} — possible side-channel leak",
                    timestamp=time.time(),
                    evidence={
                        "operation": op,
                        "samples": str(len(times)),
                        "variance_ms2": f"{variance:.2f}",
                        "threshold": str(self.VARIANCE_THRESHOLD),
                    },
                    mitre_technique="T1552.004 (Private Keys via Timing)",
                ))
        return alerts


class HNDLIndicatorDetector:
    """
    Detect Harvest Now Decrypt Later indicators:
    large encrypted data exfiltration to unusual destinations.
    """

    NAME = "HNDLIndicatorDetector"
    EXFIL_THRESHOLD_MB = 100     # per hour
    UNUSUAL_PORT_THRESHOLD = 50  # unique destination ports/hour

    def detect(self, traffic_sample: list[TrafficSample]) -> list[Alert]:
        alerts: list[Alert] = []
        # Sum bytes to each destination
        dest_bytes: dict[str, int] = {}
        dest_ports: dict[str, set] = {}
        for ev in traffic_sample:
            if ev.protocol in ("TLS", "SSL", "QUIC"):
                dest_bytes[ev.dest_ip] = dest_bytes.get(ev.dest_ip, 0) + ev.payload_bytes
                port = ev.extra.get("dest_port", 443)
                dest_ports.setdefault(ev.dest_ip, set()).add(port)

        for dest, total_bytes in dest_bytes.items():
            total_mb = total_bytes / (1024 * 1024)
            if total_mb > self.EXFIL_THRESHOLD_MB:
                severity = "CRITICAL" if total_mb > 500 else "HIGH"
                alerts.append(Alert(
                    detector=self.NAME,
                    severity=severity,
                    description=f"Large encrypted exfil to {dest} — potential HNDL collection",
                    timestamp=time.time(),
                    evidence={
                        "destination": dest,
                        "total_mb": f"{total_mb:.1f}",
                        "threshold_mb": str(self.EXFIL_THRESHOLD_MB),
                        "unique_ports": str(len(dest_ports.get(dest, set()))),
                    },
                    mitre_technique="T1048.002 (Exfiltration Over Asymmetric Encrypted Channel)",
                ))
        return alerts


class WeakCertificateDetector:
    """
    Detect certificate anomalies: weak keys, wrong algorithms, near-expiry.
    """

    NAME = "WeakCertificateDetector"

    @staticmethod
    def _is_weak_algorithm(alg: str) -> bool:
        weak = {"RSA-1024", "RSA-512", "MD5withRSA", "SHA1withRSA",
                "DSA-1024", "EC-P192"}
        return alg in weak

    def detect(self, traffic_sample: list[TrafficSample]) -> list[Alert]:
        alerts: list[Alert] = []
        for ev in traffic_sample:
            cert = ev.extra.get("certificate")
            if not cert:
                continue
            key_bits = cert.get("key_bits", 2048)
            algorithm = cert.get("algorithm", "RSA-2048")
            days_until_expiry = cert.get("days_until_expiry", 365)
            subject = cert.get("subject", ev.dest_ip)

            if self._is_weak_algorithm(algorithm) or key_bits < 2048:
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="CRITICAL",
                    description=f"Weak certificate algorithm: {algorithm} on {subject}",
                    timestamp=ev.timestamp,
                    evidence={
                        "subject": subject,
                        "algorithm": algorithm,
                        "key_bits": str(key_bits),
                        "quantum_safe": "NO",
                    },
                    mitre_technique="T1553.004 (Install Root Certificate)",
                ))
            elif days_until_expiry < 30:
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="MEDIUM",
                    description=f"Certificate near expiry ({days_until_expiry}d) on {subject}",
                    timestamp=ev.timestamp,
                    evidence={
                        "subject": subject,
                        "days_remaining": str(days_until_expiry),
                        "action": "Renew immediately",
                    },
                    mitre_technique="T1553 (Subvert Trust Controls)",
                ))
        return alerts


class JWTAnomalyDetector:
    """
    Detect JWT anomalies: algorithm confusion, expired tokens, missing jti claims.
    """

    NAME = "JWTAnomalyDetector"
    MAX_TOKEN_AGE_SECONDS = 3600   # 1 hour

    def detect(self, traffic_sample: list[TrafficSample]) -> list[Alert]:
        alerts: list[Alert] = []
        seen_jtis: set = set()
        now = time.time()

        for ev in traffic_sample:
            jwt_meta = ev.extra.get("jwt")
            if not jwt_meta:
                continue

            alg = jwt_meta.get("alg", "HS256")
            exp = jwt_meta.get("exp", now + 3600)
            iat = jwt_meta.get("iat", now)
            jti = jwt_meta.get("jti")

            # Algorithm confusion (none, HS256 on RS256-expected endpoint)
            if alg.lower() in ("none", "null"):
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="CRITICAL",
                    description=f"JWT algorithm='none' — signature bypass attempt",
                    timestamp=ev.timestamp,
                    evidence={"algorithm": alg, "source": ev.source_ip},
                    mitre_technique="T1550.001 (Application Access Token)",
                ))

            # Expired token
            if exp < now:
                age_min = (now - exp) / 60
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="HIGH",
                    description=f"Expired JWT used {age_min:.0f} min after expiry — replay?",
                    timestamp=ev.timestamp,
                    evidence={
                        "expired_mins_ago": f"{age_min:.0f}",
                        "source": ev.source_ip,
                        "jti": str(jti),
                    },
                    mitre_technique="T1550.001 (Replay Attack)",
                ))

            # JTI replay
            if jti:
                if jti in seen_jtis:
                    alerts.append(Alert(
                        detector=self.NAME,
                        severity="HIGH",
                        description=f"JWT jti={jti} used more than once — replay attack",
                        timestamp=ev.timestamp,
                        evidence={"jti": str(jti), "source": ev.source_ip},
                        mitre_technique="T1550.001 (Replay)",
                    ))
                seen_jtis.add(jti)
            else:
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="MEDIUM",
                    description="JWT missing jti claim — replay not detectable",
                    timestamp=ev.timestamp,
                    evidence={"source": ev.source_ip},
                    mitre_technique="T1550.001",
                ))
        return alerts


class SideChannelPatternDetector:
    """
    Detect power/EM side-channel patterns:
    unusual CPU/power consumption spikes during crypto operations.
    """

    NAME = "SideChannelPatternDetector"
    POWER_SPIKE_THRESHOLD = 2.5   # × baseline
    TIMING_DEVIATION_MS = 3.0

    def detect(self, traffic_sample: list[TrafficSample]) -> list[Alert]:
        alerts: list[Alert] = []
        for ev in traffic_sample:
            power = ev.extra.get("power_normalized")
            timing_dev = ev.extra.get("timing_deviation_ms")

            if power is not None and power > self.POWER_SPIKE_THRESHOLD:
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="HIGH",
                    description=f"Power spike {power:.1f}× during {ev.operation} — EM/SCA risk",
                    timestamp=ev.timestamp,
                    evidence={
                        "operation": ev.operation,
                        "power_ratio": f"{power:.1f}×",
                        "source": ev.source_ip,
                    },
                    mitre_technique="T1601 (Modify System Image — SCA inference)",
                ))

            if timing_dev is not None and abs(timing_dev) > self.TIMING_DEVIATION_MS:
                alerts.append(Alert(
                    detector=self.NAME,
                    severity="MEDIUM",
                    description=f"Timing deviation {timing_dev:.1f}ms on {ev.operation}",
                    timestamp=ev.timestamp,
                    evidence={
                        "operation": ev.operation,
                        "deviation_ms": f"{timing_dev:.2f}",
                    },
                    mitre_technique="T1552.004",
                ))
        return alerts


# ---------------------------------------------------------------------------
# Alert System (aggregator + risk scoring)
# ---------------------------------------------------------------------------

class AlertSystem:
    """
    Aggregate alerts from multiple detectors, compute risk score, classify risk level.
    """

    WEIGHTS = {"CRITICAL": 10, "HIGH": 4, "MEDIUM": 2, "LOW": 1}

    def __init__(self):
        self.detectors = [
            TimingAnomalyDetector(),
            HNDLIndicatorDetector(),
            WeakCertificateDetector(),
            JWTAnomalyDetector(),
            SideChannelPatternDetector(),
        ]

    def analyze(self, traffic: list[TrafficSample]) -> dict:
        all_alerts: list[Alert] = []
        for det in self.detectors:
            try:
                alerts = det.detect(traffic)
                all_alerts.extend(alerts)
            except Exception as exc:
                print(f"  [WARN] Detector {det.NAME} error: {exc}")

        # Compute risk score
        score = sum(self.WEIGHTS.get(a.severity, 0) for a in all_alerts)
        severity_counts = {s: sum(1 for a in all_alerts if a.severity == s)
                           for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}

        if score >= 30:
            risk_level = "CRITICAL"
        elif score >= 15:
            risk_level = "HIGH"
        elif score >= 5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "alerts": all_alerts,
            "total_alerts": len(all_alerts),
            "risk_score": score,
            "risk_level": risk_level,
            "severity_counts": severity_counts,
        }


# ---------------------------------------------------------------------------
# 24-Hour Traffic Simulation
# ---------------------------------------------------------------------------

def generate_traffic_sample(seed: int = 42) -> list[TrafficSample]:
    """
    Simulate 24 hours of network traffic (scaled to ~500 events for demo).
    Embeds: timing anomalies, HNDL exfil, weak cert, JWT replay, power spike.
    """
    rng = random.Random(seed)
    now = time.time()
    traffic: list[TrafficSample] = []
    internal_ips = ["10.0.1.10", "10.0.1.20", "10.0.1.30"]
    external_ips = ["203.0.113.10", "198.51.100.5", "192.0.2.99"]
    attacker_ip = "185.220.101.1"   # Tor exit node / attacker

    # --- Normal TLS traffic ---
    for i in range(300):
        traffic.append(TrafficSample(
            timestamp=now - rng.uniform(0, 86400),
            source_ip=rng.choice(internal_ips),
            dest_ip=rng.choice(external_ips),
            protocol="TLS",
            payload_bytes=rng.randint(1024, 50_000),
            operation="TLS_HANDSHAKE",
            extra={
                "response_time_ms": rng.gauss(10, 0.5),   # tight variance — normal
                "certificate": {
                    "subject": "api.example.com",
                    "algorithm": "RSA-2048",
                    "key_bits": 2048,
                    "days_until_expiry": rng.randint(60, 365),
                },
            },
        ))

    # --- ATTACK: Timing side-channel (high variance RSA_SIGN operations) ---
    for i in range(50):
        traffic.append(TrafficSample(
            timestamp=now - rng.uniform(3600, 7200),
            source_ip=attacker_ip,
            dest_ip=internal_ips[0],
            protocol="TLS",
            payload_bytes=256,
            operation="RSA_SIGN",
            extra={
                "response_time_ms": rng.gauss(10, 5.0),   # HIGH variance — attack
            },
        ))

    # --- ATTACK: HNDL — large encrypted exfiltration ---
    for i in range(20):
        traffic.append(TrafficSample(
            timestamp=now - rng.uniform(0, 3600),
            source_ip=internal_ips[1],
            dest_ip=attacker_ip,
            protocol="TLS",
            payload_bytes=rng.randint(10_000_000, 50_000_000),   # 10–50 MB per event
            operation="TLS_DATA",
            extra={
                "dest_port": rng.choice([443, 8443, 4433, 9001]),
                "response_time_ms": 200.0,
            },
        ))

    # --- ATTACK: Weak certificate ---
    traffic.append(TrafficSample(
        timestamp=now - 1800,
        source_ip=attacker_ip,
        dest_ip=internal_ips[0],
        protocol="TLS",
        payload_bytes=1024,
        operation="TLS_HANDSHAKE",
        extra={
            "certificate": {
                "subject": "legacy-api.internal",
                "algorithm": "RSA-1024",
                "key_bits": 1024,
                "days_until_expiry": 5,
            }
        },
    ))

    # --- ATTACK: JWT replay (expired token + JTI reuse) ---
    expired_exp = now - 3600   # expired 1 hour ago
    for i in range(5):
        traffic.append(TrafficSample(
            timestamp=now - rng.uniform(0, 300),
            source_ip=attacker_ip,
            dest_ip=internal_ips[2],
            protocol="JWT",
            payload_bytes=512,
            operation="JWT_VERIFY",
            extra={
                "jwt": {
                    "alg": "HS256",
                    "exp": expired_exp,
                    "iat": expired_exp - 900,
                    "jti": "stolen-tok-xyz",   # same JTI each time = replay
                }
            },
        ))

    # --- ATTACK: JWT algorithm=none bypass ---
    traffic.append(TrafficSample(
        timestamp=now - 600,
        source_ip=attacker_ip,
        dest_ip=internal_ips[0],
        protocol="JWT",
        payload_bytes=256,
        operation="JWT_VERIFY",
        extra={
            "jwt": {
                "alg": "none",
                "exp": now + 7200,
                "iat": now,
                "jti": "crafted-tok-001",
            }
        },
    ))

    # --- ATTACK: Power/EM side-channel spike ---
    for i in range(8):
        traffic.append(TrafficSample(
            timestamp=now - rng.uniform(7200, 10800),
            source_ip=attacker_ip,
            dest_ip=internal_ips[0],
            protocol="API",
            payload_bytes=64,
            operation="ECDSA_SIGN",
            extra={
                "power_normalized": rng.uniform(3.0, 5.0),   # 3–5× baseline spike
                "timing_deviation_ms": rng.uniform(4.0, 8.0),
            },
        ))

    return traffic


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    print("\n" + "#" * 72)
    print("  ATTACK DETECTION AND MONITORING SYSTEM")
    print("  Simulating 24-hour traffic with embedded attack patterns")
    print("#" * 72)

    traffic = generate_traffic_sample(seed=42)
    print(f"\n  Traffic events generated: {len(traffic)}")
    print(f"  Attack events embedded: timing anomaly, HNDL exfil, weak cert, "
          "JWT replay, alg=none, power spike")
    print("\n  Running detectors...\n")

    alert_system = AlertSystem()
    t0 = time.perf_counter()
    report = alert_system.analyze(traffic)
    elapsed = (time.perf_counter() - t0) * 1000

    alerts: list[Alert] = report["alerts"]

    # Display all alerts grouped by severity
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        group = [a for a in alerts if a.severity == sev]
        if group:
            print(f"\n  --- {sev} ALERTS ({len(group)}) ---")
            for alert in group:
                alert.display()

    # Risk assessment
    print("\n\n" + "=" * 72)
    print("  RISK ASSESSMENT REPORT")
    print("=" * 72)
    print(f"  Total alerts       : {report['total_alerts']}")
    for sev, count in report["severity_counts"].items():
        print(f"  {sev:<12}       : {count}")
    print(f"  Risk Score         : {report['risk_score']}")
    print(f"  Risk Level         : {report['risk_level']}")
    print(f"  Detection time     : {elapsed:.1f} ms")
    print("=" * 72)

    # MITRE ATT&CK coverage
    techniques = sorted(set(a.mitre_technique for a in alerts if a.mitre_technique))
    print(f"\n  MITRE ATT&CK Techniques Detected: {len(techniques)}")
    for t in techniques:
        print(f"    • {t}")

    # Recommendations
    print("\n  IMMEDIATE ACTIONS REQUIRED:")
    if any(a.severity == "CRITICAL" for a in alerts):
        print("  [!!!] CRITICAL alerts active — escalate to CISO immediately")
    if any("HNDL" in a.detector for a in alerts):
        print("  [!!!] Encrypted exfiltration detected — block destination IPs, "
              "start PQC migration NOW")
    if any("alg=none" in a.description for a in alerts):
        print("  [!!!] JWT alg=none bypass detected — patch JWT library, rotate secrets")
    if any("RSA-1024" in str(a.evidence) for a in alerts):
        print("  [!!] Weak certificate in use — replace with RSA-3072 or ECDSA P-384")
    print()


if __name__ == "__main__":
    main()
