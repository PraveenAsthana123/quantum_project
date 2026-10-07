# User Stories — qc-cryptography-module

## US-01: NIST KAT Vector Validation
**As a** cryptography researcher,
**I want** NIST Known Answer Test (KAT) vectors for BB84, ML-KEM, ML-DSA, and SLH-DSA,
**So that** I can validate my implementations against authoritative reference outputs.

**Acceptance Criteria:**
- KAT vectors stored in `data/kat_vectors.csv` with input_hex, expected_output_hex, test_type
- At least 5 KAT vectors per major algorithm (ML-KEM, ML-DSA, BB84)
- `pytest tests/test_known_answers.py` verifies all KAT entries automatically

---

## US-02: BB84 QKD Simulation
**As a** security engineer,
**I want** a BB84 QKD simulation with eavesdropping detection,
**So that** I can understand quantum key distribution and demonstrate its security properties.

**Acceptance Criteria:**
- Simulates Alice preparing qubits, Eve intercepting (optional), Bob measuring
- Reports key rate (bits/round), QBER (quantum bit error rate), detection probability
- Eavesdropping introduces measurable QBER ≥ 25% (provable threshold)

---

## US-03: Shor's Algorithm Working Example
**As a** developer,
**I want** working code for Shor's algorithm on small integers (N ≤ 35),
**So that** I can understand quantum factoring and its threat to RSA.

**Acceptance Criteria:**
- Factorizes N = 15, 21, 35 correctly without requiring a real quantum computer
- Shows the order-finding quantum subroutine structure
- Reports qubit count estimate for realistic RSA-2048 attack

---

## US-04: Grover's Oracle for AES
**As a** student,
**I want** Grover's oracle simulation showing quadratic speedup,
**So that** I can see how Grover's algorithm reduces AES-128 effective key strength to 64 bits.

**Acceptance Criteria:**
- Oracle circuit simulation for a toy n-bit search space
- Iteration count = O(√N) verified for small N (n ≤ 8 bits)
- Security level impact table: AES-128 → 64 bits effective, AES-256 → 128 bits effective

---

## US-05: Automated KAT Testing
**As a** compliance tester,
**I want** automated KAT tests that can be run in CI,
**So that** I can verify all 24 cryptography modules pass known answer tests on every commit.

**Acceptance Criteria:**
- `pytest tests/test_known_answers.py` runs without external services
- Each module has at least one KAT-style deterministic test
- Test report shows pass/fail per algorithm with timing

---

## US-06: Entropy Analysis Tools
**As a** researcher,
**I want** entropy analysis tools comparing quantum vs classical randomness sources,
**So that** I can validate that quantum-safe keys use sufficient entropy.

**Acceptance Criteria:**
- Min-entropy calculation for bit strings from `data/quantum_entropy.csv`
- Comparison: QRNG entropy vs PRNG entropy for same output length
- NIST SP 800-90B conformance notes documented per source

---

## US-07: Protocol Comparison for Algorithm Selection
**As an** architect,
**I want** protocol comparison data across all 24 modules,
**So that** I can select the appropriate quantum-safe algorithm for each use case.

**Acceptance Criteria:**
- Decision matrix: use case → module → algorithm → key size → performance tier
- Coverage: key exchange, digital signatures, random number generation, secret sharing
- Performance benchmarks included for representative operations

---

## US-08: Reproducible Test Vectors for CI
**As a** QA engineer,
**I want** reproducible test vectors with fixed seeds,
**So that** I can regression-test all 24 crypto module implementations on every build.

**Acceptance Criteria:**
- All test data generated with `random.seed(42)` or equivalent fixed seed
- `python src/generate_data.py` is idempotent (same output every run)
- Deterministic test vectors documented in `data/kat_vectors.csv`
