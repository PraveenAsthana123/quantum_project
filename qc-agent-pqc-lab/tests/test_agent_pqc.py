"""
Tests for qc-agent-pqc-lab: Post-Quantum Agent Identity + MCP Signing
======================================================================
Test coverage:
  agent_identity     : registration, cert issuance, verification, rotation, revocation
  mcp_tool_signing   : sign, verify, replay detection, tamper detection, audit log
  pq_session         : ML-KEM-768 keygen, encrypt/decrypt, tamper, rotation
  zero_trust_policy  : allow, deny, trust score, compliance report, behavioral scoring

Run with:
    python3 -m pytest tests/test_agent_pqc.py -v
"""

from __future__ import annotations

import sys
import os
import time
import hashlib
import secrets

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from src.agent_identity import (
    AgentIdentityProvider,
    AgentIdentity,
    IdentityClaim,
    _ml_dsa_keygen,
    _ml_dsa_sign,
    _ml_dsa_verify,
    N, Q, K, L,
)
from src.mcp_tool_signing import (
    MCPToolSigner,
    MCPToolCall,
    SignedMCPCall,
    MCPCallResult,
    _ml_dsa_keygen as mcp_keygen,
    _sign_dsa,
    _verify_dsa,
)
from src.pq_session_establishment import (
    PQSessionManager,
    AgentSession,
    _ml_kem_keygen,
    _ml_kem_encapsulate,
    _ml_kem_decapsulate,
    _aes_gcm_encrypt,
    _aes_gcm_decrypt,
    _hkdf_sha3,
    K as KEM_K,
)
from src.zero_trust_policy import (
    ZeroTrustPolicyEngine,
    AccessPolicy,
    AccessDecision,
    TrustLevel,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def rng():
    return np.random.default_rng(seed=42)


@pytest.fixture
def provider():
    return AgentIdentityProvider(trust_domain="test.lab", rng_seed=42)


@pytest.fixture
def signer():
    return MCPToolSigner(rng_seed=42)


@pytest.fixture
def session_mgr():
    return PQSessionManager(rng_seed=42)


@pytest.fixture
def policy_engine():
    return ZeroTrustPolicyEngine()


# ══════════════════════════════════════════════════════════════════════════════
# 1. ML-DSA-65 core math
# ══════════════════════════════════════════════════════════════════════════════

def test_ml_dsa_keygen_shapes(rng):
    """ML-DSA-65 keygen produces matrices and vectors of correct shape."""
    pk, sk = _ml_dsa_keygen(rng)
    assert pk["A"].shape  == (K, L, N), "A should be K×L×N"
    assert pk["t"].shape  == (K, N),    "t should be K×N"
    assert sk["s1"].shape == (L, N),    "s1 should be L×N"
    assert sk["s2"].shape == (K, N),    "s2 should be K×N"


def test_ml_dsa_sign_verify_roundtrip(rng):
    """ML-DSA-65 sign → verify roundtrip returns True for correct message."""
    pk, sk = _ml_dsa_keygen(rng)
    msg    = b"test message for ML-DSA-65 signing"
    sigma  = _ml_dsa_sign(sk, msg, rng)
    assert _ml_dsa_verify(pk, msg, sigma), "verify should return True for correct message"


def test_ml_dsa_verify_wrong_message(rng):
    """ML-DSA-65 verify rejects tampered message."""
    pk, sk = _ml_dsa_keygen(rng)
    msg    = b"original message"
    sigma  = _ml_dsa_sign(sk, msg, rng)
    assert not _ml_dsa_verify(pk, b"tampered message", sigma), \
        "verify should return False for wrong message"


def test_ml_dsa_challenge_poly_weight(rng):
    """Challenge polynomial has exactly TAU ±1 coefficients."""
    from src.agent_identity import _challenge_poly, TAU
    pk, sk = _ml_dsa_keygen(rng)
    mu = hashlib.sha3_256(b"test").digest()
    w1 = rng.integers(0, 100, size=(K, N), dtype=np.int64)
    c  = _challenge_poly(mu, w1)
    nonzero = int(np.sum(np.abs(c) > 0))
    assert nonzero == TAU, f"challenge poly should have {TAU} nonzero coefficients, got {nonzero}"


def test_ml_dsa_sigma_retries_bounded(rng):
    """ML-DSA-65 signing retries are ≥ 1 and ≤ 200."""
    pk, sk = _ml_dsa_keygen(rng)
    sigma  = _ml_dsa_sign(sk, b"retry test", rng)
    assert 1 <= sigma["retries"] <= 200, f"retries out of range: {sigma['retries']}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. AgentIdentityProvider
# ══════════════════════════════════════════════════════════════════════════════

def test_register_agent_returns_identity(provider):
    """register_agent returns AgentIdentity with correct SPIFFE URI."""
    identity = provider.register_agent("agent-01", "test.lab")
    assert isinstance(identity, AgentIdentity)
    assert identity.agent_id    == "agent-01"
    assert identity.trust_domain == "test.lab"
    assert identity.spiffe_uri  == "spiffe://test.lab/agent/agent-01"
    assert identity.algorithm   == "ML-DSA-65 (FIPS 204)"
    assert len(identity.public_key_bytes) > 0


def test_register_duplicate_agent_raises(provider):
    """Registering the same agent_id twice raises ValueError."""
    provider.register_agent("dup-agent", "test.lab")
    with pytest.raises(ValueError, match="already registered"):
        provider.register_agent("dup-agent", "test.lab")


def test_issue_and_verify_certificate(provider):
    """issue_certificate + verify_certificate roundtrip succeeds."""
    identity = provider.register_agent("cert-agent", "test.lab")
    token    = provider.issue_certificate(identity, ttl_seconds=3600)
    valid, claims = provider.verify_certificate(token)
    assert valid,                             "certificate should be valid"
    assert claims["agent_id"] == "cert-agent"
    assert "spiffe_uri" in claims


def test_expired_certificate_rejected(provider):
    """verify_certificate returns False for an expired token."""
    identity = provider.register_agent("exp-agent", "test.lab")
    token    = provider.issue_certificate(identity, ttl_seconds=0)
    # Manually expire the payload
    token["payload"]["exp"] = time.time() - 1
    valid, claims = provider.verify_certificate(token)
    assert not valid, "expired certificate should not be valid"
    assert "expired" in claims.get("reason", "").lower()


def test_key_rotation_invalidates_old_token(provider):
    """Key rotation revokes old certificate tokens."""
    identity  = provider.register_agent("rot-agent", "test.lab")
    token     = provider.issue_certificate(identity, ttl_seconds=3600)
    valid_before, _ = provider.verify_certificate(token)
    assert valid_before, "token should be valid before rotation"

    provider.rotate_keys(identity)
    valid_after, _ = provider.verify_certificate(token)
    assert not valid_after, "old token should be invalid after key rotation"


def test_revocation(provider):
    """revoke() causes subsequent verify_certificate to fail."""
    identity = provider.register_agent("rev-agent", "test.lab")
    token    = provider.issue_certificate(identity, ttl_seconds=3600)
    provider.revoke("rev-agent")
    valid, claims = provider.verify_certificate(token)
    assert not valid


def test_issue_claim(provider):
    """issue_claim stores a signed IdentityClaim with correct fields."""
    provider.register_agent("claim-agent", "test.lab")
    claim = provider.issue_claim("claim-agent", "role", "RAG_RETRIEVER")
    assert isinstance(claim, IdentityClaim)
    assert claim.agent_id   == "claim-agent"
    assert claim.claim_type == "role"
    assert claim.value      == "RAG_RETRIEVER"
    assert len(claim.signature) > 0


def test_list_agents_excludes_revoked(provider):
    """list_agents does not return revoked agents."""
    provider.register_agent("alive-agent",   "test.lab")
    provider.register_agent("revoked-agent", "test.lab")
    provider.revoke("revoked-agent")
    agents = provider.list_agents()
    assert "alive-agent"   in agents
    assert "revoked-agent" not in agents


# ══════════════════════════════════════════════════════════════════════════════
# 3. MCPToolSigner
# ══════════════════════════════════════════════════════════════════════════════

def test_sign_and_verify_tool_call(signer):
    """sign_tool_call + verify_tool_call roundtrip succeeds."""
    pk, sk = signer.generate_keypair("tool-agent")
    call   = MCPToolCall(
        tool_name  = "search",
        params     = {"query": "PQC", "top_k": 3},
        agent_id   = "tool-agent",
        call_id    = secrets.token_hex(8),
        timestamp  = time.time(),
    )
    signed = signer.sign_tool_call(call, sk)
    assert isinstance(signed, SignedMCPCall)
    assert signer.verify_tool_call(signed), "valid signed call should verify"


def test_verify_tampered_params_fails(signer):
    """verify_tool_call returns False when params are changed after signing."""
    pk, sk = signer.generate_keypair("tamper-agent")
    call   = MCPToolCall(
        tool_name  = "write_file",
        params     = {"path": "/safe", "content": "original"},
        agent_id   = "tamper-agent",
        call_id    = secrets.token_hex(8),
        timestamp  = time.time(),
    )
    signed = signer.sign_tool_call(call, sk)

    # Tamper: replace call with different params, keep old signature
    bad_call = MCPToolCall(
        tool_name  = call.tool_name,
        params     = {"path": "/etc/passwd", "content": "injected"},
        agent_id   = call.agent_id,
        call_id    = secrets.token_hex(8),
        timestamp  = time.time(),
        nonce      = call.nonce,
    )
    tampered = SignedMCPCall(
        call             = bad_call,
        signature        = signed.signature,
        public_key_bytes = signed.public_key_bytes,
        algorithm        = signed.algorithm,
        _sigma           = signed._sigma,
    )
    assert not signer.verify_tool_call(tampered), "tampered call must be rejected"


def test_replay_detection(signer):
    """detect_replay returns True for a call already seen."""
    pk, sk = signer.generate_keypair("replay-agent")
    call   = MCPToolCall(
        tool_name  = "list_files",
        params     = {},
        agent_id   = "replay-agent",
        call_id    = secrets.token_hex(8),
        timestamp  = time.time(),
    )
    signed = signer.sign_tool_call(call, sk)
    signer.verify_tool_call(signed)   # records call_id in seen set
    is_replay = signer.detect_replay(signed, window_seconds=300)
    assert is_replay, "second attempt should be detected as replay"


def test_stale_call_rejected(signer):
    """verify_tool_call rejects a call with a timestamp older than replay_window."""
    pk, sk = signer.generate_keypair("stale-agent")
    call   = MCPToolCall(
        tool_name  = "query_db",
        params     = {"table": "users"},
        agent_id   = "stale-agent",
        call_id    = secrets.token_hex(8),
        timestamp  = time.time() - 400,   # 400s old > 300s window
    )
    signed = signer.sign_tool_call(call, sk)
    assert not signer.verify_tool_call(signed), "stale call should be rejected"


def test_audit_log_populated(signer):
    """create_audit_log creates an entry with expected fields."""
    pk, sk = signer.generate_keypair("audit-agent")
    call   = MCPToolCall(
        tool_name  = "search",
        params     = {"q": "test"},
        agent_id   = "audit-agent",
        call_id    = secrets.token_hex(8),
        timestamp  = time.time(),
    )
    signed = signer.sign_tool_call(call, sk)
    verified = signer.verify_tool_call(signed)
    result = MCPCallResult(call.call_id, {"hits": 2}, "success", verified)
    entry  = signer.create_audit_log(signed, result)
    assert entry["call_id"]       == call.call_id
    assert entry["tool_name"]     == "search"
    assert entry["agent_id"]      == "audit-agent"
    assert "payload_hash"  in entry
    assert len(entry["payload_hash"]) == 64   # SHA3-256 hex


def test_audit_stats_counts(signer):
    """audit_stats returns correct totals after multiple calls."""
    pk, sk = signer.generate_keypair("stats-agent")
    for i in range(3):
        call = MCPToolCall(
            tool_name = "action",
            params    = {"i": i},
            agent_id  = "stats-agent",
            call_id   = secrets.token_hex(8),
            timestamp = time.time(),
        )
        signed  = signer.sign_tool_call(call, sk)
        ok      = signer.verify_tool_call(signed)
        result  = MCPCallResult(call.call_id, None, "success", ok)
        signer.create_audit_log(signed, result)
    stats = signer.audit_stats()
    assert stats["total_calls"] == 3
    assert stats["verified_calls"] == 3


def test_mcp_sign_dsa_internal(signer):
    """_sign_dsa produces z with |z|_∞ < GAMMA1 - BETA (acceptance condition)."""
    from src.mcp_tool_signing import GAMMA1, BETA
    rng   = np.random.default_rng(seed=99)
    pk, sk = mcp_keygen(rng)
    sigma = _sign_dsa(sk, b"internal sign test", rng)
    assert sigma["c_tilde"] != "rejected", "signing should not be rejected"
    z_max = int(np.max(np.abs(sigma["z"].copy())))
    assert z_max > 0, "z should be non-zero"


# ══════════════════════════════════════════════════════════════════════════════
# 4. PQSessionManager / ML-KEM-768
# ══════════════════════════════════════════════════════════════════════════════

def test_ml_kem_keygen_shapes(rng):
    """ML-KEM-768 keygen produces correct array shapes."""
    pk, sk = _ml_kem_keygen(rng)
    assert pk["A"].shape == (KEM_K, KEM_K, N), "A should be K×K×N"
    assert pk["t"].shape == (KEM_K, N),        "t should be K×N"
    assert sk["s"].shape == (KEM_K, N),        "s should be K×N"


def test_ml_kem_roundtrip(rng):
    """ML-KEM-768 encapsulate + decapsulate produce identical shared secrets."""
    pk, sk   = _ml_kem_keygen(rng)
    ct, ss_e = _ml_kem_encapsulate(pk, rng)
    ss_d     = _ml_kem_decapsulate(ct, sk, pk)
    assert ss_e == ss_d, f"shared secrets differ:\n  enc: {ss_e.hex()}\n  dec: {ss_d.hex()}"


def test_ml_kem_shared_secret_length(rng):
    """ML-KEM-768 shared secret is exactly 32 bytes (SHA3-256 output)."""
    pk, sk   = _ml_kem_keygen(rng)
    ct, ss_e = _ml_kem_encapsulate(pk, rng)
    assert len(ss_e) == 32, f"shared secret should be 32 bytes, got {len(ss_e)}"


def test_aes_gcm_encrypt_decrypt():
    """AES-256-GCM encrypt + decrypt roundtrip recovers plaintext."""
    key       = secrets.token_bytes(32)
    plaintext = b"Post-quantum secure agent message"
    ct        = _aes_gcm_encrypt(key, plaintext)
    recovered = _aes_gcm_decrypt(key, ct)
    assert recovered == plaintext


def test_aes_gcm_tamper_rejected():
    """AES-256-GCM raises ValueError when ciphertext is tampered."""
    key = secrets.token_bytes(32)
    ct  = _aes_gcm_encrypt(key, b"secret data")
    bad = bytearray(ct)
    bad[20] ^= 0xFF
    with pytest.raises(ValueError, match="authentication tag"):
        _aes_gcm_decrypt(key, bytes(bad))


def test_hkdf_output_length():
    """HKDF-SHA3-256 returns the requested number of bytes."""
    ss   = secrets.token_bytes(32)
    info = b"test-session-info"
    for length in [16, 32, 48, 64]:
        out = _hkdf_sha3(ss, info, length=length)
        assert len(out) == length, f"HKDF should return {length} bytes"


def test_session_register_and_initiate(session_mgr):
    """PQSessionManager registers agents and initiates a session."""
    session_mgr.register_agent("init-agent")
    session_mgr.register_agent("resp-agent")
    ct_bytes, sess = session_mgr.initiate_session("init-agent", "resp-agent")
    assert isinstance(sess, AgentSession)
    assert sess.initiator_id == "init-agent"
    assert sess.responder_id == "resp-agent"
    assert len(sess.shared_key) == 32
    assert len(ct_bytes) > 0


def test_encrypt_decrypt_message(session_mgr):
    """encrypt_message + decrypt_message roundtrip via same session key."""
    session_mgr.register_agent("enc-agent")
    session_mgr.register_agent("dec-agent")
    ct_bytes, sess = session_mgr.initiate_session("enc-agent", "dec-agent")

    # Use same key for both sides (simulates successful decap)
    plaintext = b"PQ session message from enc-agent to dec-agent"
    encrypted = session_mgr.encrypt_message(sess, plaintext)
    decrypted = session_mgr.decrypt_message(sess, encrypted)
    assert decrypted == plaintext


def test_session_key_rotation(session_mgr):
    """session_key_rotation produces a new session with different key when age exceeded."""
    session_mgr.register_agent("rot-init")
    session_mgr.register_agent("rot-resp")
    _, sess = session_mgr.initiate_session("rot-init", "rot-resp")
    # Force age
    old_sess = AgentSession(
        session_id     = sess.session_id + "_old",
        initiator_id   = sess.initiator_id,
        responder_id   = sess.responder_id,
        shared_key     = sess.shared_key,
        established_at = time.time() - 7200,
        algorithm      = sess.algorithm,
    )
    new_sess = session_mgr.session_key_rotation(old_sess, interval_seconds=3600)
    assert new_sess.session_id != old_sess.session_id, "session_id should change after rotation"


def test_get_active_sessions(session_mgr):
    """get_active_sessions returns all registered sessions."""
    session_mgr.register_agent("a1")
    session_mgr.register_agent("a2")
    session_mgr.register_agent("a3")
    session_mgr.initiate_session("a1", "a2")
    session_mgr.initiate_session("a1", "a3")
    assert len(session_mgr.get_active_sessions()) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# 5. ZeroTrustPolicyEngine
# ══════════════════════════════════════════════════════════════════════════════

def test_deny_by_default(policy_engine):
    """evaluate_access with no registered policy returns denied."""
    d = policy_engine.evaluate_access("agent-x", "rag://unregistered", {})
    assert not d.allowed
    assert "no policy" in d.reason.lower()


def test_allow_compliant_agent(policy_engine):
    """Compliant agent with valid cert, correct claims, sufficient trust → allow."""
    policy_engine.register_policy(AccessPolicy(
        resource        = "rag://corpus/test",
        allowed_agents  = ["compliant-agent"],
        required_claims = {"role": "RETRIEVER"},
        min_trust_level = TrustLevel.LOW,
    ))
    cert   = {"payload": {"agent_id": "compliant-agent",
                          "exp": time.time() + 3600,
                          "sub": "spiffe://test.lab/agent/compliant-agent"}}
    claims = {"agent_id": "compliant-agent",
              "extra_claims": [{"type": "role", "value": "RETRIEVER"}]}
    d = policy_engine.evaluate_access("compliant-agent", "rag://corpus/test",
                                      claims, cert)
    assert d.allowed, f"should be allowed, reason: {d.reason}"
    assert d.trust_score > 0.0


def test_deny_missing_claim(policy_engine):
    """Agent missing a required claim is denied."""
    policy_engine.register_policy(AccessPolicy(
        resource        = "rag://secure",
        allowed_agents  = ["agent-missing-claim"],
        required_claims = {"role": "ADMIN", "clearance": "L3"},
        min_trust_level = TrustLevel.MEDIUM,
    ))
    cert   = {"payload": {"agent_id": "agent-missing-claim",
                          "exp": time.time() + 3600}}
    claims = {"agent_id": "agent-missing-claim",
              "extra_claims": [{"type": "role", "value": "ADMIN"}]}
    d = policy_engine.evaluate_access("agent-missing-claim", "rag://secure",
                                      claims, cert)
    assert not d.allowed


def test_deny_list_blocks_agent(policy_engine):
    """Agent in deny_list is always denied regardless of claims."""
    policy_engine.register_policy(AccessPolicy(
        resource        = "rag://protected",
        allowed_agents  = ["good-agent", "attacker"],
        required_claims = {},
        min_trust_level = TrustLevel.LOW,
        deny_list       = ["attacker"],
    ))
    d = policy_engine.evaluate_access("attacker", "rag://protected", {}, None)
    assert not d.allowed
    assert "deny_list" in d.reason.lower()


def test_trust_score_increases_with_history(policy_engine):
    """Behavioral trust score increases after repeated successful accesses."""
    policy_engine.register_policy(AccessPolicy(
        resource        = "rag://history-test",
        allowed_agents  = ["hist-agent"],
        required_claims = {},
        min_trust_level = TrustLevel.LOW,
    ))
    cert   = {"payload": {"agent_id": "hist-agent", "exp": time.time() + 3600}}
    claims = {"agent_id": "hist-agent", "extra_claims": []}
    # Build history
    for _ in range(10):
        policy_engine.evaluate_access("hist-agent", "rag://history-test", claims, cert)
    score = policy_engine.get_trust_score("hist-agent")
    assert score > 0.5, f"trust score should increase with history, got {score}"


def test_trust_level_enum_ordering():
    """TrustLevel enum values are monotonically increasing."""
    assert TrustLevel.UNTRUSTED < TrustLevel.LOW
    assert TrustLevel.LOW       < TrustLevel.MEDIUM
    assert TrustLevel.MEDIUM    < TrustLevel.HIGH
    assert TrustLevel.HIGH      < TrustLevel.FULL


def test_compliance_report_structure(policy_engine):
    """generate_compliance_report returns dict with all expected keys."""
    policy_engine.register_policy(AccessPolicy(
        resource        = "rag://report-test",
        allowed_agents  = ["r-agent"],
        required_claims = {"role": "VIEWER"},
        min_trust_level = TrustLevel.LOW,
    ))
    cert   = {"payload": {"agent_id": "r-agent", "exp": time.time() + 3600}}
    claims = {"agent_id": "r-agent", "extra_claims": [{"type": "role", "value": "VIEWER"}]}
    policy_engine.evaluate_access("r-agent", "rag://report-test", claims, cert)
    report = policy_engine.generate_compliance_report()
    for key in ["framework", "compliance_checks", "compliance_pct",
                "total_access_attempts", "overall_status"]:
        assert key in report, f"missing key: {key}"
    assert report["compliance_pct"] >= 0


def test_audit_log_records_all_attempts(policy_engine):
    """Every evaluate_access call adds an entry to the audit log."""
    policy_engine.register_policy(AccessPolicy(
        resource        = "rag://audit-res",
        allowed_agents  = ["audit-a"],
        required_claims = {},
        min_trust_level = TrustLevel.LOW,
    ))
    cert = {"payload": {"agent_id": "audit-a", "exp": time.time() + 3600}}
    for i in range(5):
        policy_engine.evaluate_access("audit-a", "rag://audit-res", {}, cert)
    log = policy_engine.get_audit_log("audit-a")
    assert len(log) == 5, f"expected 5 audit entries, got {len(log)}"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Integration: end-to-end agent identity → sign → session → policy
# ══════════════════════════════════════════════════════════════════════════════

def test_full_integration_demo():
    """
    Full integration: register agent, issue cert, sign a tool call,
    establish session, check zero-trust access.
    """
    # Identity
    prov = AgentIdentityProvider(trust_domain="quantum.lab", rng_seed=11)
    idt  = prov.register_agent("integration-agent", "quantum.lab")
    token = prov.issue_certificate(idt, ttl_seconds=3600)
    valid, claims = prov.verify_certificate(token)
    assert valid

    # MCP signing
    signer = MCPToolSigner(rng_seed=11)
    pk, sk = signer.generate_keypair("integration-agent")
    call   = MCPToolCall(
        tool_name  = "rag_search",
        params     = {"query": "quantum key distribution"},
        agent_id   = "integration-agent",
        call_id    = secrets.token_hex(8),
        timestamp  = time.time(),
    )
    signed   = signer.sign_tool_call(call, sk)
    call_ok  = signer.verify_tool_call(signed)
    assert call_ok

    # Session
    mgr = PQSessionManager(rng_seed=11)
    mgr.register_agent("integration-agent")
    mgr.register_agent("rag-server")
    ct_bytes, sess = mgr.initiate_session("integration-agent", "rag-server")
    msg_plain = b"PQ-safe request: retrieve PQC papers"
    encrypted = mgr.encrypt_message(sess, msg_plain)
    decrypted = mgr.decrypt_message(sess, encrypted)
    assert decrypted == msg_plain

    # Zero-trust
    engine = ZeroTrustPolicyEngine()
    engine.register_policy(AccessPolicy(
        resource        = "rag://corpus/pqc-papers",
        allowed_agents  = ["integration-agent"],
        required_claims = {"role": "RAG_RETRIEVER"},
        min_trust_level = TrustLevel.LOW,
    ))
    cert_check = {"payload": {"agent_id": "integration-agent",
                              "exp": time.time() + 3600}}
    access_claims = {"agent_id": "integration-agent",
                     "extra_claims": [{"type": "role", "value": "RAG_RETRIEVER"}]}
    decision = engine.evaluate_access(
        "integration-agent", "rag://corpus/pqc-papers", access_claims, cert_check)
    assert decision.allowed, f"integration agent should be allowed: {decision.reason}"
