# QC Agent PQC Lab — Post-Quantum Identity for AI Agents

Post-quantum cryptographic identity, tool-call signing, session establishment,
and Zero Trust policy enforcement for AI agent workloads.

**Standards:** NIST FIPS 203 (ML-KEM-768), NIST FIPS 204 (ML-DSA-65), NIST SP 800-207 (Zero Trust)
**Security:** IND-CCA2 + EUF-CMA under Module-LWE; 178-bit classical/quantum security

---

## Modules

| File | Purpose | Algorithm |
|------|---------|-----------|
| `src/agent_identity.py` | SPIFFE workload identity + certificate issuance | ML-DSA-65 (FIPS 204) |
| `src/mcp_tool_signing.py` | Signed MCP tool calls + replay detection | ML-DSA-65 (FIPS 204) |
| `src/pq_session_establishment.py` | Agent-to-agent session key establishment | ML-KEM-768 (FIPS 203) + AES-256-GCM |
| `src/zero_trust_policy.py` | Zero Trust policy engine | NIST SP 800-207 + ML-DSA-65 verify |

## Quick Start

```bash
cd /mnt/deepa/quantum/qc-agent-pqc-lab
pip install -r requirements.txt

# Run each module's demo
python3 src/agent_identity.py
python3 src/mcp_tool_signing.py
python3 src/pq_session_establishment.py
python3 src/zero_trust_policy.py

# Run all 20+ tests
python3 -m pytest tests/test_agent_pqc.py -v
```

## Architecture

```
AI Agent
  │
  ├─ AgentIdentityProvider   (ML-DSA-65 keypair + SPIFFE URI + certificate)
  │    └─ issue_certificate() → JWT-style token signed with ML-DSA-65 root key
  │
  ├─ MCPToolSigner           (every tool call signed before dispatch)
  │    └─ sign_tool_call()   → SignedMCPCall (c_tilde + z vector)
  │    └─ detect_replay()    → nonce + 5-min sliding window
  │
  ├─ PQSessionManager        (ML-KEM-768 encapsulate/decapsulate)
  │    └─ initiate_session() → ciphertext_bytes + AgentSession
  │    └─ encrypt_message()  → AES-256-GCM (key from HKDF-SHA3-256)
  │
  └─ ZeroTrustPolicyEngine   (NIST SP 800-207)
       └─ evaluate_access()  → trust_score = 0.4×cert + 0.3×claims + 0.3×behavioral
```

## Security Properties

| Property | Mechanism |
|----------|-----------|
| Agent authentication | ML-DSA-65 certificate signed by provider root key |
| Tool-call integrity | ML-DSA-65 signature over canonical call bytes (all fields) |
| Replay prevention | call_id nonce + 5-minute sliding timestamp window |
| Session confidentiality | ML-KEM-768 → HKDF-SHA3-256 → AES-256-GCM |
| Session authentication | AES-GCM authentication tag (16 bytes, SHAKE-256) |
| Access control | Deny-by-default; allowlist + claim check + trust score |
| Behavioral trust | Rolling score: +0.05 per success, −0.15 per denial |
| Quantum safety | Module-LWE / Module-SIS; secure against Shor/Grover |

## Key Parameters

**ML-DSA-65 (FIPS 204):** N=256, Q=8380417, K=6, L=5, η=4, γ₁=2¹⁷, τ=49
**ML-KEM-768 (FIPS 203):** N=256, Q=3329, K=3, η₁=η₂=2, dᵤ=10, dᵥ=4
