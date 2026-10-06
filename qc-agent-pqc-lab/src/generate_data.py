"""
Agent PQC Lab — Synthetic Data Generator
==========================================
Purpose  : Generate four synthetic datasets that simulate a post-quantum
           secured AI-agent mesh operating under Zero Trust.

Outputs (all written to ../data/)
---------------------------------
  agent_registry.json   — 20 registered agents with PQC identities
  tool_call_log.csv     — 500 MCP tool call records (signed + verified)
  session_log.csv       — 200 ML-KEM-768 session records
  policy_decisions.csv  — 300 Zero Trust access-control decisions

Usage
-----
    python generate_data.py
"""
from __future__ import annotations

import csv
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

# ── Reproducible seed ─────────────────────────────────────────────────────────
random.seed(7)

# ── Paths ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

AGENT_REGISTRY_JSON  = os.path.join(DATA_DIR, "agent_registry.json")
TOOL_CALL_LOG_CSV    = os.path.join(DATA_DIR, "tool_call_log.csv")
SESSION_LOG_CSV      = os.path.join(DATA_DIR, "session_log.csv")
POLICY_DECISIONS_CSV = os.path.join(DATA_DIR, "policy_decisions.csv")

# ── Constants ─────────────────────────────────────────────────────────────────
ALGORITHMS  = ["ML-DSA-65", "ML-KEM-768", "SLH-DSA-128f", "FALCON-512"]
TRUST_DOMAINS = ["finance.corp", "healthcare.corp", "logistics.corp",
                 "research.corp", "infra.corp"]
TOOLS = [
    "read_file", "write_file", "execute_code", "query_db", "call_api",
    "send_message", "fetch_secret", "deploy_model", "scan_network", "audit_log",
]
RESOURCES = [
    "/api/payments", "/api/health-records", "/api/routing",
    "/api/models", "/api/secrets", "/api/audit",
    "/api/deployments", "/api/network",
]
AGENT_STATUSES = ["active", "active", "active", "suspended", "revoked"]

# ── Key size lookup (bytes) ───────────────────────────────────────────────────
KEY_SIZES = {
    "ML-DSA-65":   {"public_key_bytes": 1952, "private_key_bytes": 4032,
                    "sig_bytes": 3309, "security_level": 178},
    "ML-KEM-768":  {"public_key_bytes": 1184, "private_key_bytes": 2400,
                    "shared_secret_bytes": 32, "security_level": 178},
    "SLH-DSA-128f":{"public_key_bytes": 32,   "private_key_bytes": 64,
                    "sig_bytes": 17088, "security_level": 128},
    "FALCON-512":  {"public_key_bytes": 897,  "private_key_bytes": 1281,
                    "sig_bytes": 666,   "security_level": 103},
}

BASE_TIME = datetime(2026, 1, 1)


def _ts(offset_hours: float) -> str:
    dt = BASE_TIME + timedelta(hours=offset_hours)
    return dt.isoformat() + "Z"


# ── Agent registry ────────────────────────────────────────────────────────────

def _make_agent(idx: int) -> Dict[str, Any]:
    algo   = random.choice(["ML-DSA-65", "SLH-DSA-128f", "FALCON-512"])
    domain = random.choice(TRUST_DOMAINS)
    ks     = KEY_SIZES[algo]
    status = random.choices(AGENT_STATUSES, weights=[60, 60, 60, 10, 5])[0]
    return {
        "agent_id":        f"AGENT-{uuid.uuid4().hex[:8].upper()}",
        "display_name":    f"agent-{domain.split('.')[0]}-{idx:03d}",
        "trust_domain":    domain,
        "algorithm":       algo,
        "public_key_bytes":ks["public_key_bytes"],
        "private_key_seed":uuid.uuid4().hex,   # placeholder seed
        "cert_serial":     f"CERT-{uuid.uuid4().hex[:12].upper()}",
        "issued_at":       _ts(idx * 24),
        "expires_at":      _ts(idx * 24 + 8760),  # +1 year
        "status":          status,
        "security_bits":   ks["security_level"],
    }


def generate_agent_registry(n: int = 20) -> List[Dict[str, Any]]:
    agents = [_make_agent(i) for i in range(n)]
    with open(AGENT_REGISTRY_JSON, "w") as fh:
        json.dump({"agents": agents, "count": len(agents),
                   "generated_at": datetime.utcnow().isoformat() + "Z"}, fh, indent=2)
    print(f"[generate_data] Wrote {n} agents → {AGENT_REGISTRY_JSON}")
    return agents


# ── Tool call log ─────────────────────────────────────────────────────────────

def generate_tool_call_log(agents: List[Dict[str, Any]], n: int = 500) -> None:
    agent_ids = [a["agent_id"] for a in agents]
    fieldnames = ["call_id", "agent_id", "tool_name", "timestamp",
                  "verified", "latency_ms", "replay_detected",
                  "sig_size_bytes", "algorithm"]

    with open(TOOL_CALL_LOG_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            agent_id = random.choice(agent_ids)
            agent    = next(a for a in agents if a["agent_id"] == agent_id)
            algo     = agent["algorithm"]
            ks       = KEY_SIZES[algo]
            verified = 1 if random.random() < 0.97 else 0
            replay   = 1 if (not verified and random.random() < 0.3) else 0
            writer.writerow({
                "call_id":        f"CALL-{uuid.uuid4().hex[:10].upper()}",
                "agent_id":       agent_id,
                "tool_name":      random.choice(TOOLS),
                "timestamp":      _ts(i * 0.5),
                "verified":       verified,
                "latency_ms":     round(random.uniform(0.8, 8.0), 2),
                "replay_detected":replay,
                "sig_size_bytes": ks.get("sig_bytes", 3309),
                "algorithm":      algo,
            })
    print(f"[generate_data] Wrote {n} tool calls → {TOOL_CALL_LOG_CSV}")


# ── Session log ───────────────────────────────────────────────────────────────

def generate_session_log(agents: List[Dict[str, Any]], n: int = 200) -> None:
    agent_ids = [a["agent_id"] for a in agents]
    fieldnames = ["session_id", "initiator", "responder", "established_at",
                  "duration_s", "key_algorithm", "shared_key_bits",
                  "messages_exchanged", "encap_time_ms", "decap_time_ms"]

    with open(SESSION_LOG_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            init, resp = random.sample(agent_ids, 2)
            writer.writerow({
                "session_id":       f"SES-{uuid.uuid4().hex[:10].upper()}",
                "initiator":        init,
                "responder":        resp,
                "established_at":   _ts(i * 1.2),
                "duration_s":       random.randint(60, 7200),
                "key_algorithm":    "ML-KEM-768",
                "shared_key_bits":  256,
                "messages_exchanged": random.randint(1, 500),
                "encap_time_ms":    round(random.uniform(0.5, 3.0), 2),
                "decap_time_ms":    round(random.uniform(0.3, 2.5), 2),
            })
    print(f"[generate_data] Wrote {n} sessions → {SESSION_LOG_CSV}")


# ── Policy decisions ──────────────────────────────────────────────────────────

def generate_policy_decisions(agents: List[Dict[str, Any]], n: int = 300) -> None:
    agent_ids = [a["agent_id"] for a in agents]
    fieldnames = ["decision_id", "agent_id", "resource", "allowed",
                  "trust_score", "latency_ms", "timestamp",
                  "deny_reason"]

    with open(POLICY_DECISIONS_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            agent_id   = random.choice(agent_ids)
            trust      = round(random.uniform(0.0, 1.0), 3)
            allowed    = 1 if trust >= 0.6 else 0
            deny_reason= "" if allowed else random.choice(
                ["trust_score_below_threshold", "cert_expired",
                 "resource_policy_deny", "behavioral_anomaly"])
            writer.writerow({
                "decision_id":  f"DEC-{uuid.uuid4().hex[:10].upper()}",
                "agent_id":     agent_id,
                "resource":     random.choice(RESOURCES),
                "allowed":      allowed,
                "trust_score":  trust,
                "latency_ms":   round(random.uniform(0.1, 2.0), 2),
                "timestamp":    _ts(i * 0.8),
                "deny_reason":  deny_reason,
            })
    print(f"[generate_data] Wrote {n} policy decisions → {POLICY_DECISIONS_CSV}")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate() -> None:
    agents = generate_agent_registry(20)
    generate_tool_call_log(agents, 500)
    generate_session_log(agents, 200)
    generate_policy_decisions(agents, 300)


if __name__ == "__main__":
    generate()
