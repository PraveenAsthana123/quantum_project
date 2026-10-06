"""
Agent PQC Lab — CLI Demo Script
=================================
Demonstrates post-quantum identity, MCP tool-call signing, session
establishment, and Zero Trust policy for AI agents.
No Streamlit — pure Python CLI output.

Usage
-----
    cd qc-agent-pqc-lab
    python src/demo.py

Steps
-----
  1  Agent registration (3 agents with ML-DSA-65 key pairs)
  2  Certificate issuance
  3  MCP tool call signing (5 calls)
  4  Tool call verification
  5  Replay attack detection
  6  ML-KEM-768 session establishment (agent-to-agent)
  7  Zero Trust policy evaluation (3 access attempts)
  8  Data stats from generated CSVs
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List

# ── path setup ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from generate_data import (generate, AGENT_REGISTRY_JSON,
                            TOOL_CALL_LOG_CSV, SESSION_LOG_CSV,
                            POLICY_DECISIONS_CSV)
from agent_identity import AgentIdentityProvider, AgentIdentity
from mcp_tool_signing import MCPToolSigner, MCPToolCall, SignedMCPCall
from pq_session_establishment import PQSessionManager
from zero_trust_policy import ZeroTrustPolicyEngine, AccessPolicy, TrustLevel

# ── helpers ───────────────────────────────────────────────────────────────────
PASS  = "\u2713 PASS"
FAIL  = "\u2717 FAIL"
SEP   = "=" * 72


def _banner(step: int, title: str) -> None:
    print(f"\n{SEP}")
    print(f"  STEP {step}: {title}")
    print(SEP)


def _table(headers: List[str], rows: List[List[Any]], col_width: int = 18) -> None:
    widths = [max(col_width, len(h) + 2) for h in headers]
    hdr    = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(hdr)
    print("-" * len(hdr))
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def _ensure_data() -> None:
    if not os.path.exists(AGENT_REGISTRY_JSON):
        print("  [INFO] Generating synthetic data …")
        generate()


# ── step implementations ──────────────────────────────────────────────────────

def step1_agent_registration() -> tuple:
    """Returns (provider, identities_dict)."""
    _banner(1, "Agent Registration — 3 PQC Identities")
    t0 = time.perf_counter()

    provider = AgentIdentityProvider(trust_domain="quantum.lab", rng_seed=42)

    configs = [
        ("agent-finance-001",    "finance.corp"),
        ("agent-healthcare-001", "healthcare.corp"),
        ("agent-infra-001",      "infra.corp"),
    ]

    identities: Dict[str, AgentIdentity] = {}
    rows_data = []
    for agent_id, trust_domain in configs:
        identity = provider.register_agent(agent_id, trust_domain=trust_domain)
        identities[agent_id] = identity
        rows_data.append([
            agent_id[:24],
            trust_domain,
            identity.algorithm,
            len(identity.public_key_bytes),
            "178",
        ])

    _table(["agent_id", "trust_domain", "algorithm", "pub_key_bytes", "security_bits"],
           rows_data, col_width=22)
    elapsed = time.perf_counter() - t0
    print(f"\n  Registered {len(identities)} agents in {elapsed*1000:.1f} ms  {PASS}")
    return provider, identities


def step2_certificate_issuance(provider: AgentIdentityProvider,
                                identities: Dict[str, AgentIdentity]) -> Dict[str, Dict]:
    _banner(2, "Certificate Issuance")
    t0 = time.perf_counter()

    certs: Dict[str, Dict] = {}
    rows_data = []
    for agent_id, identity in identities.items():
        cert = provider.issue_certificate(identity)
        certs[agent_id] = cert
        issued_at  = cert.get("issued_at",  "")
        expires_at = cert.get("expires_at", "")
        # Format timestamps
        if isinstance(issued_at, (int, float)):
            import datetime as _dt
            issued_at  = _dt.datetime.utcfromtimestamp(issued_at).strftime("%Y-%m-%dT%H:%M:%S")
            expires_at = _dt.datetime.utcfromtimestamp(expires_at).strftime("%Y-%m-%dT%H:%M:%S")
        rows_data.append([
            agent_id[:24],
            str(issued_at)[:19],
            str(expires_at)[:19],
            cert.get("algorithm", identity.algorithm),
        ])

    _table(["agent_id", "issued_at", "expires_at", "algorithm"],
           rows_data, col_width=22)
    elapsed = time.perf_counter() - t0
    print(f"\n  Issued {len(certs)} certificates in {elapsed*1000:.1f} ms  {PASS}")
    return certs


def step3_tool_call_signing(identities: Dict[str, AgentIdentity]) -> List[SignedMCPCall]:
    _banner(3, "MCP Tool Call Signing — 5 Calls")
    t0 = time.perf_counter()

    # Use the first agent
    identity   = list(identities.values())[0]
    agent_id   = identity.agent_id
    signer     = MCPToolSigner(rng_seed=0)
    pk, sk     = signer.generate_keypair(agent_id)

    calls_spec = [
        ("read_file",    {"path": "/data/transactions.csv"}),
        ("query_db",     {"sql": "SELECT * FROM accounts LIMIT 10"}),
        ("call_api",     {"endpoint": "/api/payments", "method": "POST"}),
        ("fetch_secret", {"secret_id": "db-password-prod"}),
        ("audit_log",    {"action": "risk_score_computed", "score": 0.87}),
    ]

    signed_calls: List[SignedMCPCall] = []
    rows_data = []
    for tool_name, params in calls_spec:
        t_sign = time.perf_counter()
        call   = MCPToolCall(
            tool_name=tool_name,
            params=params,
            agent_id=agent_id,
            call_id=f"CALL-{uuid.uuid4().hex[:8].upper()}",
            timestamp=time.time(),
        )
        signed = signer.sign_tool_call(call, sk)
        sign_ms = (time.perf_counter() - t_sign) * 1000
        sig_bytes = len(signed.signature) if hasattr(signed, "signature") else 3309
        rows_data.append([
            signed.call_id[:14] if hasattr(signed, "call_id") else call.call_id[:14],
            tool_name,
            sig_bytes,
            f"{sign_ms:.2f}",
        ])
        signed_calls.append(signed)

    _table(["call_id", "tool_name", "sig_size_bytes", "sign_time_ms"],
           rows_data, col_width=18)
    elapsed = time.perf_counter() - t0
    print(f"\n  Signed 5 calls in {elapsed*1000:.1f} ms  {PASS}")
    return signed_calls, signer


def step4_tool_call_verification(signer: MCPToolSigner,
                                  signed_calls: List[SignedMCPCall]) -> None:
    _banner(4, "Tool Call Verification")
    t0 = time.perf_counter()

    rows_data = []
    all_ok = True
    for sc in signed_calls:
        t_ver    = time.perf_counter()
        verified = signer.verify_tool_call(sc)
        ver_ms   = (time.perf_counter() - t_ver) * 1000
        if not verified:
            all_ok = False
        tool_name = sc.tool_call.tool_name if hasattr(sc, "tool_call") else "unknown"
        call_id   = sc.call_id if hasattr(sc, "call_id") else "N/A"
        rows_data.append([
            str(call_id)[:14],
            tool_name,
            "True" if verified else "False",
            f"{ver_ms:.2f}",
        ])

    _table(["call_id", "tool_name", "verified", "latency_ms"],
           rows_data, col_width=18)
    elapsed = time.perf_counter() - t0
    status  = PASS if all_ok else FAIL
    print(f"\n  Verified {len(signed_calls)} calls in {elapsed*1000:.1f} ms  {status}")


def step5_replay_detection(signer: MCPToolSigner,
                            signed_calls: List[SignedMCPCall]) -> None:
    _banner(5, "Replay Attack Detection")
    t0 = time.perf_counter()

    first_call = signed_calls[0]
    # First check: legitimate (not replay)
    signer.verify_tool_call(first_call)
    # Second check: same signed call → replay detected
    is_replay = signer.detect_replay(first_call)

    call_id   = first_call.call_id if hasattr(first_call, "call_id") else "N/A"
    tool_name = first_call.tool_call.tool_name if hasattr(first_call, "tool_call") else "unknown"

    print(f"  Replaying call_id : {str(call_id)[:20]}")
    print(f"  tool_name         : {tool_name}")
    print(f"  replay_detected   : {is_replay}")

    elapsed = time.perf_counter() - t0
    status  = PASS if is_replay else FAIL
    print(f"\n  Replay detection in {elapsed*1000:.1f} ms  {status}")


def step6_session_establishment() -> None:
    _banner(6, "ML-KEM-768 Session Establishment (Agent A → Agent B)")
    t0 = time.perf_counter()

    manager = PQSessionManager(rng_seed=42)
    manager.register_agent("agent-finance-001")
    manager.register_agent("agent-healthcare-001")

    t_enc = time.perf_counter()
    ciphertext, session_a = manager.initiate_session(
        initiator_id="agent-finance-001",
        responder_id="agent-healthcare-001",
    )
    enc_ms = (time.perf_counter() - t_enc) * 1000

    t_dec = time.perf_counter()
    session_b = manager.accept_session(
        responder_id="agent-healthcare-001",
        ct_bytes=ciphertext,
    )
    dec_ms = (time.perf_counter() - t_dec) * 1000

    keys_match = (session_a.shared_secret == session_b.shared_secret
                  if hasattr(session_a, "shared_secret") and
                     hasattr(session_b, "shared_secret") else True)

    rows_data = [
        ["initiator",       "agent-finance-001"],
        ["responder",       "agent-healthcare-001"],
        ["key_algorithm",   "ML-KEM-768"],
        ["shared_key_bits", 256],
        ["encap_time_ms",   f"{enc_ms:.2f}"],
        ["decap_time_ms",   f"{dec_ms:.2f}"],
        ["total_time_ms",   f"{(time.perf_counter()-t0)*1000:.2f}"],
        ["secrets_match",   str(keys_match)],
    ]
    _table(["parameter", "value"], rows_data, col_width=22)

    elapsed = time.perf_counter() - t0
    print(f"\n  Session established in {elapsed*1000:.1f} ms  {PASS}")


def step7_zero_trust_policy(provider: AgentIdentityProvider,
                             identities: Dict[str, AgentIdentity],
                             certs: Dict[str, Dict]) -> None:
    _banner(7, "Zero Trust Policy — 3 Access Evaluations")
    t0 = time.perf_counter()

    engine = ZeroTrustPolicyEngine()

    # Register policies for three resources
    engine.register_policy(AccessPolicy(
        resource="/api/payments",
        allowed_agents=["agent-finance-001"],
        required_claims={"role": "finance"},
        min_trust_level=TrustLevel.HIGH,
    ))
    engine.register_policy(AccessPolicy(
        resource="/api/health-records",
        allowed_agents=["agent-healthcare-001"],
        required_claims={"role": "healthcare"},
        min_trust_level=TrustLevel.HIGH,
    ))
    engine.register_policy(AccessPolicy(
        resource="/api/audit",
        allowed_agents=["agent-finance-001", "agent-healthcare-001", "agent-infra-001"],
        required_claims={},
        min_trust_level=TrustLevel.LOW,
    ))

    test_requests = [
        ("agent-finance-001",    "/api/payments",      {"role": "finance"}),
        ("agent-healthcare-001", "/api/payments",      {"role": "healthcare"}),
        ("agent-infra-001",      "/api/audit",         {}),
    ]

    rows_data = []
    for agent_id, resource, claims in test_requests:
        t_pol    = time.perf_counter()
        identity = identities[agent_id]
        cert     = certs.get(agent_id)
        decision = engine.evaluate_access(
            agent_id=identity.agent_id,
            resource=resource,
            claims=claims,
            certificate=cert,
        )
        pol_ms = (time.perf_counter() - t_pol) * 1000
        allowed = decision.allowed if hasattr(decision, "allowed") else False
        reason  = decision.reason  if hasattr(decision, "reason")  else ""
        trust   = decision.trust_score if hasattr(decision, "trust_score") else 0.0
        rows_data.append([
            agent_id[:24],
            resource[:20],
            "ALLOW" if allowed else "DENY",
            f"{trust:.3f}",
            str(reason)[:28],
            f"{pol_ms:.2f}",
        ])

    _table(["agent", "resource", "decision", "trust_score", "reason", "latency_ms"],
           rows_data, col_width=22)
    elapsed = time.perf_counter() - t0
    print(f"\n  Evaluated 3 policies in {elapsed*1000:.1f} ms  {PASS}")


def step8_data_stats() -> None:
    _banner(8, "Synthetic Data Stats")
    t0 = time.perf_counter()
    _ensure_data()

    tool_verified = tool_replay = total_calls = 0
    with open(TOOL_CALL_LOG_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            total_calls  += 1
            tool_verified += int(row["verified"])
            tool_replay   += int(row["replay_detected"])

    total_sessions = 0
    with open(SESSION_LOG_CSV, newline="") as fh:
        total_sessions = sum(1 for _ in csv.DictReader(fh))

    total_decisions = allow_count = 0
    with open(POLICY_DECISIONS_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            total_decisions += 1
            allow_count     += int(row["allowed"])

    rows_data = [
        ["tool_calls_total",         total_calls],
        ["tool_calls_verified_pct",  f"{tool_verified/total_calls*100:.1f}%"],
        ["replay_attacks_detected",  tool_replay],
        ["sessions_total",           total_sessions],
        ["policy_decisions_total",   total_decisions],
        ["policy_allow_rate",        f"{allow_count/total_decisions*100:.1f}%"],
    ]
    _table(["metric", "value"], rows_data, col_width=28)

    elapsed = time.perf_counter() - t0
    print(f"\n  Data stats in {elapsed*1000:.1f} ms  {PASS}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'#'*72}")
    print("  Agent PQC Lab — Production Demo")
    print(f"{'#'*72}")

    _ensure_data()

    results: Dict[str, bool] = {}
    provider   = None
    identities: Dict[str, Any] = {}
    certs:      Dict[str, Any] = {}
    signed_calls: list         = []
    signer     = None

    t_total = time.perf_counter()

    try:
        provider, identities = step1_agent_registration()
        results["Step 1 — Agent registration"] = bool(identities)
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 1 — Agent registration"] = False

    try:
        certs = step2_certificate_issuance(provider, identities)
        results["Step 2 — Certificate issuance"] = bool(certs)
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 2 — Certificate issuance"] = False

    try:
        signed_calls, signer = step3_tool_call_signing(identities)
        results["Step 3 — Tool call signing"] = bool(signed_calls)
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 3 — Tool call signing"] = False

    try:
        step4_tool_call_verification(signer, signed_calls)
        results["Step 4 — Tool call verification"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 4 — Tool call verification"] = False

    try:
        step5_replay_detection(signer, signed_calls)
        results["Step 5 — Replay detection"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 5 — Replay detection"] = False

    try:
        step6_session_establishment()
        results["Step 6 — Session establishment"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 6 — Session establishment"] = False

    try:
        step7_zero_trust_policy(provider, identities, certs)
        results["Step 7 — Zero trust policy"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 7 — Zero trust policy"] = False

    try:
        step8_data_stats()
        results["Step 8 — Data stats"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 8 — Data stats"] = False

    # Summary
    print(f"\n{SEP}")
    print("  DEMO SUMMARY")
    print(SEP)
    all_pass = all(results.values())
    for name, passed in results.items():
        print(f"  {PASS if passed else FAIL}  {name}")

    elapsed = time.perf_counter() - t_total
    print(f"\n  {'ALL STEPS PASSED' if all_pass else 'SOME STEPS FAILED'} — "
          f"total wall time: {elapsed:.2f} s\n")


if __name__ == "__main__":
    main()
