# Agent PQC Lab — User Stories

Version: 1.0 | Date: 2026-10-06 | Lab: qc-agent-pqc-lab

---

## US-01 — AI Security Engineer: Post-Quantum Agent Identity

**As an** AI security engineer building a multi-agent orchestration system,
**I want to** assign each agent a post-quantum cryptographic identity (ML-DSA-65) at registration,
**So that** every tool call and session can be cryptographically attributed to a specific agent even after quantum computers break RSA/ECDSA.

**Acceptance Criteria:**
- AgentIdentity generates an ML-DSA-65 key pair on construction
- Public key bytes, security bits (178), and trust domain are inspectable
- Certificate issuance returns issued_at, expires_at, algorithm, and cert_serial
- Registration completes in under 500 ms on commodity hardware

---

## US-02 — Platform Architect: MCP Tool Call Signing

**As a** platform architect designing an MCP-based agentic workflow,
**I want to** sign every tool call with the agent's PQC private key before dispatch,
**So that** downstream services can verify the call originated from a trusted agent and has not been tampered with.

**Acceptance Criteria:**
- MCPToolSigner.sign_call() attaches a signature, nonce, timestamp, and call_id
- Signature size matches ML-DSA-65 spec (3309 bytes)
- Sign time under 10 ms per call
- Signed payload is a self-contained JSON-serializable dict

---

## US-03 — AI Security Engineer: Replay Attack Prevention

**As an** AI security engineer operating an agent mesh,
**I want to** detect and reject replayed tool calls (same nonce reused),
**So that** an adversary who intercepts a signed call cannot re-execute it later.

**Acceptance Criteria:**
- First verify() of a call succeeds and registers the nonce
- Second verify() of the same call sets replay_detected=True
- Nonce window is configurable (default: 60 seconds)
- Replay detection adds under 1 ms overhead per verification

---

## US-04 — CISO: Zero Trust Access Control

**As a** CISO responsible for AI agent access governance,
**I want to** enforce per-resource policies (min_trust, allowed_domains) evaluated on every access,
**So that** agents from the wrong trust domain or with low behavioral scores are denied access to sensitive resources.

**Acceptance Criteria:**
- ZeroTrustPolicyEngine.evaluate() returns allowed, trust_score, and reason
- Trust score formula: 0.4×cert_valid + 0.3×claims_complete + 0.3×behavioral_score
- Deny decisions include a machine-readable reason code
- Policy evaluation latency under 2 ms

---

## US-05 — Platform Architect: ML-KEM-768 Agent Sessions

**As a** platform architect designing agent-to-agent communication,
**I want to** establish a quantum-safe shared session key using ML-KEM-768,
**So that** all inter-agent messages are encrypted with a key that cannot be broken by Shor's algorithm.

**Acceptance Criteria:**
- Initiator calls initiate_session(responder_public_key) → returns ciphertext + shared_secret
- Responder calls respond_to_session(ciphertext) → derives identical shared_secret
- Shared secret is 256 bits (AES-256-GCM key)
- Full handshake completes in under 10 ms

---

## US-06 — DevOps Engineer: Synthetic Data for Load Testing

**As a** DevOps engineer stress-testing the agent security pipeline,
**I want to** generate realistic synthetic datasets (tool call logs, session logs, policy decisions),
**So that** I can benchmark the system under 500 concurrent tool-call verifications without real production data.

**Acceptance Criteria:**
- generate_data.py produces tool_call_log.csv (500 rows), session_log.csv (200 rows), policy_decisions.csv (300 rows)
- Data includes realistic latency distributions, 97% verification rate, and replay flag
- All files written to data/ directory
- Generation completes in under 5 seconds

---

## US-07 — AI Security Engineer: Algorithm Diversity Support

**As an** AI security engineer managing a heterogeneous agent fleet,
**I want to** register agents using different PQC algorithms (ML-DSA-65, SLH-DSA-128f, FALCON-512),
**So that** the system is not tied to a single algorithm and can migrate gracefully if one is weakened.

**Acceptance Criteria:**
- AgentIdentity accepts algorithm parameter: ML-DSA-65, SLH-DSA-128f, FALCON-512
- Public key bytes, signature sizes, and security bits differ correctly per algorithm
- Demo prints a side-by-side comparison table of all three
- Algorithm metadata (key sizes, security bits) stored in KEY_SIZES registry

---

## US-08 — CISO: Audit Trail for Compliance

**As a** CISO needing evidence for SOC 2 / ISO 27001 compliance audits,
**I want to** view a summary of all agent tool calls, session establishments, and policy decisions with timestamps,
**So that** I can demonstrate to auditors that every agent action was authenticated and authorized.

**Acceptance Criteria:**
- tool_call_log.csv includes call_id, agent_id, tool_name, timestamp, verified, replay_detected
- policy_decisions.csv includes decision_id, agent_id, resource, allowed, trust_score, deny_reason
- session_log.csv includes session_id, initiator, responder, key_algorithm, duration_s
- Demo step 8 prints aggregated stats: verification rate, replay count, allow rate
