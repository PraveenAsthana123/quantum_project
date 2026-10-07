# User Stories — qc-crypto-lab

## US-01: PQC Migration Justification
**As a** cryptographer,
**I want to** compare RSA, ECDSA, and ML-DSA signature performance,
**So that** I can justify PQC migration to stakeholders with concrete benchmark data.

**Acceptance Criteria:**
- Key generation, sign, and verify times shown for RSA-2048, RSA-4096, ECDSA-P256, ECDSA-P384, Ed25519, ML-DSA-44, ML-DSA-65, ML-DSA-87
- Size comparison table (public key bytes, signature bytes)
- NIST security level mapped for each algorithm

---

## US-02: Classical Crypto Vulnerability Testing
**As a** security engineer,
**I want to** test classical crypto implementations against known vulnerabilities,
**So that** I can identify which systems are exposed to quantum attacks before migration.

**Acceptance Criteria:**
- Shor's algorithm threat model per RSA key size
- Grover's effective key size reduction for AES
- HNDL (Harvest Now Decrypt Later) risk window estimate

---

## US-03: Hybrid Encryption Code Examples
**As a** developer,
**I want** code examples for hybrid encryption (KEM + AES-GCM),
**So that** I can implement quantum-safe encrypted channels in production.

**Acceptance Criteria:**
- ML-KEM-768 key encapsulation + AES-256-GCM symmetric encryption example
- Key derivation flow documented (KEM shared secret → KDF → AES key)
- Error handling and key lifecycle shown

---

## US-04: Entropy Source Analysis
**As a** security researcher,
**I want to** analyze entropy sources and key generation quality,
**So that** I can validate that quantum-safe keys are generated with sufficient randomness.

**Acceptance Criteria:**
- QRNG vs PRNG entropy comparison
- Min-entropy calculation for key material
- NIST SP 800-90B conformance checks documented

---

## US-05: Crypto Algorithm Selection Guide
**As an** architect,
**I want** a crypto algorithm selection guide based on use case and performance requirements,
**So that** I can make evidence-based decisions when designing new systems.

**Acceptance Criteria:**
- Decision matrix: use case → recommended algorithm
- Performance vs security level tradeoffs shown
- Migration priority rankings (high/medium/low) per algorithm family

---

## US-06: Worked Crypto Examples
**As a** student,
**I want** worked examples of RSA, ECDH, AES, and SHA-3,
**So that** I understand how modern cryptographic primitives function before studying PQC.

**Acceptance Criteria:**
- RSA key generation and sign/verify walkthrough
- ECDH shared secret derivation step-by-step
- AES-256-GCM encrypt/decrypt example
- SHA-3-256 hash computation with intermediate state

---

## US-07: Deprecated Algorithm Inventory
**As a** compliance officer,
**I want** a crypto inventory tool that identifies deprecated algorithms,
**So that** I can report quantum-vulnerable assets and track remediation progress.

**Acceptance Criteria:**
- Scan a list of algorithm identifiers against a quantum-safe/vulnerable classification
- Output: system_id, algorithm, quantum_safe flag, recommended_replacement, priority
- Export as CSV for import into compliance tracking tools

---

## US-08: Classical vs Post-Quantum Benchmarks
**As a** developer,
**I want** benchmark results comparing classical vs post-quantum crypto performance,
**So that** I can estimate the computational overhead of PQC migration in my application.

**Acceptance Criteria:**
- Benchmarks for keygen, sign/encaps, verify/decaps in milliseconds
- Overhead multiplier: PQC time / classical equivalent time
- Hardware profile noted (CPU, OS, Python version)
