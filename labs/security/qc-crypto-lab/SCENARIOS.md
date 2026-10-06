# QC Crypto Lab — Customer Demo Scenarios
> Based on: Quantum Cryptography Course (Semester VIII, 45 hrs, 3 credits)
> Updated: 2026-10-01

Legend: ✅ Implemented | 🔄 Partial | ❌ Pending

---

## Module 1 — Foundations of Quantum Mechanics & Cryptography

| # | Scenario | Demo Pitch | Status | File |
|---|----------|-----------|--------|------|
| M1-S1 | **Qubit & Superposition Visualiser** | Show a qubit rotating on the Bloch sphere; demonstrate superposition vs classical bit | ✅ Implemented | `module1-foundations/src/qubit_demo.py` |
| M1-S2 | **Quantum Entanglement Demo** | Generate Bell pairs, show correlated measurements regardless of distance | ✅ Implemented | `module1-foundations/src/entanglement_demo.py` |
| M1-S3 | **No-Cloning Theorem Proof** | Attempt to clone a qubit, prove it's impossible, show why this secures QKD | ✅ Implemented | `module1-foundations/src/no_cloning_demo.py` |
| M1-S4 | **Shor's Algorithm — RSA Threat** | Factor a small semiprime (N=15, 21) with Shor's on simulator; extrapolate threat to RSA-2048 | ✅ Implemented | `module1-foundations/src/shors_algorithm.py` |
| M1-S5 | **Grover's Algorithm — Search Speedup** | Show quadratic speedup over classical search; AES key-space reduction impact | ✅ Implemented | `module1-foundations/src/grovers_algorithm.py` |
| M1-S6 | **Classical vs Quantum Crypto Comparison** | Side-by-side table: RSA/AES/ECDSA vs ML-KEM/ML-DSA/BB84 — security, speed, key size | ✅ Implemented | `../pqc-control-tower/src/pqc_benchmark.py` |
| M1-S7 | **Quantum Fourier Transform** | QFT matrix (O(n²) gates), period finding for N=15 a=2 r=4, QFT vs DFT comparison, IQFT round-trip | ✅ Implemented | `module1-foundations/src/quantum_fourier_transform.py` |
| M1-S8 | **Quantum Phase Estimation (QPE)** | Estimate φ where U\|ψ⟩=e^(2πiφ)\|ψ⟩; T-gate φ=1/8=0.001 binary; t=4/6/8 precision table; Shor connection | ✅ Implemented | `module1-foundations/src/quantum_phase_estimation.py` |
| M1-S9 | **Quantum Walk on a Line** | Discrete-time walk T=50/100/200; Hadamard coin; σ≈T/√2 vs σ≈√T classical; graph search O(√N); element distinctness O(N^(1/3)) | ✅ Implemented | `module1-foundations/src/quantum_walk.py` |

---

## Module 2 — Quantum Key Distribution (QKD) Protocols

| # | Scenario | Demo Pitch | Status | File |
|---|----------|-----------|--------|------|
| M2-S1 | **BB84 Protocol — Full Simulation** | Alice→Bob key exchange, basis reconciliation, QBER, eavesdropper detection | ✅ Implemented | `../qc-security-lab/src/qkd_bb84.py` |
| M2-S2 | **BB84 — Privacy Amplification** | Post-sifting hash compression to eliminate Eve's partial information | ✅ Implemented | `module2-qkd/src/bb84_privacy_amplification.py` |
| M2-S3 | **B92 Protocol** | 2-state QKD (simpler than BB84); show why fewer states = less sifting overhead | ✅ Implemented | `module2-qkd/src/b92_protocol.py` |
| M2-S4 | **E91 Protocol — Entanglement-Based QKD** | Bell pairs shared between Alice & Bob; CHSH inequality test as eavesdrop detector; 3 scenarios (no Eve / full intercept / partial); BB84 vs E91 table | ✅ Implemented | `../qc-security-lab/src/e91_qkd.py` |
| M2-S5 | **CV-QKD — Continuous Variable** | Gaussian state encoding (coherent states); homodyne detection; channel capacity | ✅ Implemented | `module2-qkd/src/cv_qkd.py` |
| M2-S6 | **Fiber-Optic QKD Channel Model** | Photon loss vs distance curve; realistic range limits (100–200 km); repeater need | ✅ Implemented | `module2-qkd/src/fiber_qkd_channel.py` |
| M2-S7 | **QKD Security Proof — Info-Theoretic** | Show unconditional security bound; contrast with computational security of RSA | ✅ Implemented | `module2-qkd/src/qkd_security_proof.py` |

---

## Module 3 — Quantum Attacks & Security Analysis

| # | Scenario | Demo Pitch | Status | File |
|---|----------|-----------|--------|------|
| M3-S1 | **Intercept-Resend Attack on BB84** | Eve intercepts every qubit, resends best guess; show 25% QBER spike | ✅ Implemented | `module3-attacks/src/intercept_resend_attack.py` |
| M3-S2 | **Photon Number Splitting (PNS) Attack** | Multi-photon pulse exploit; Eve splits photon, waits for basis announcement | ✅ Implemented | `module3-attacks/src/pns_attack.py` |
| M3-S3 | **Trojan Horse Attack Simulation** | Bright light injection into Bob's device; side-information leakage model | ✅ Implemented | `module3-attacks/src/trojan_horse_attack.py` |
| M3-S4 | **Side-Channel Attack Analysis** | Timing/power analysis on naive RSA implementation vs hardened version | ✅ Implemented | `module3-attacks/src/side_channel_analysis.py` |
| M3-S5 | **QRNG — Quantum Random Number Generator** | Measure superposition qubits for true randomness; compare to PRNG bias | ✅ Implemented | `module3-attacks/src/qrng.py` |
| M3-S6 | **MDI-QKD — Measurement-Device-Independent** | Relay-based protocol immune to detector side-channels; Bell measurement at relay | ✅ Implemented | `module3-attacks/src/mdi_qkd.py` |
| M3-S7 | **Grover Attack on AES** | Simulate Grover search reducing AES-128 to 2^64 effective key space | ✅ Implemented | `module3-attacks/src/grover_aes_attack.py` |

---

## Module 4 — Post-Quantum Cryptography (PQC)

| # | Scenario | Demo Pitch | Status | File |
|---|----------|-----------|--------|------|
| M4-S1 | **ML-KEM (Kyber) Benchmark** | Key encapsulation: keygen, encap, decap timing vs RSA; key size comparison | ✅ Implemented | `../qc-security-lab/src/pqc_benchmark.py` |
| M4-S2 | **ML-DSA (Dilithium) Benchmark** | Digital signatures: keygen, sign, verify timing vs ECDSA | ✅ Implemented | `../qc-security-lab/src/pqc_benchmark.py` |
| M4-S3 | **SLH-DSA (SPHINCS+) Benchmark** | Hash-based signatures: stateless, conservative; size vs speed tradeoff | ✅ Implemented | `../pqc-control-tower/src/pqc_benchmark.py` |
| M4-S4 | **Falcon Benchmark** | Lattice signatures (NTRU-based): compact sigs, fast verify | ✅ Implemented | `../qc-security-lab/src/pqc_benchmark.py` |
| M4-S5 | **LWE — Learning With Errors Demo** | Hardness of LWE; show why quantum computers can't solve it efficiently | ✅ Implemented | `module4-pqc/src/lwe_demo.py` |
| M4-S6 | **NTRU Lattice Encryption** | Historical lattice crypto; show relationship to modern ML-KEM | ✅ Implemented | `module4-pqc/src/ntru_demo.py` |
| M4-S7 | **McEliece Code-Based Crypto** | Error-correcting code hardness; large keys but quantum-resistant since 1978 | ✅ Implemented | `module4-pqc/src/mceliece_demo.py` |
| M4-S8 | **BIKE / HQC — NIST Alternates** | Compact code-based KEMs; compare to ML-KEM on size/speed | ✅ Implemented | `module4-pqc/src/bike_hqc_demo.py` |
| M4-S9 | **Rainbow Multivariate Signatures** | Multivariate polynomial hardness; broken in 2022 — show why it failed | ✅ Implemented | `module4-pqc/src/rainbow_demo.py` |
| M4-S10 | **Hybrid Classical-PQC System** | TLS handshake with X25519+ML-KEM-768 dual encapsulation | ✅ Implemented | `module4-pqc/src/hybrid_pqc_tls.py` |
| M4-S11 | **PQC Algorithm Comparison Dashboard** | All 8 NIST finalists side-by-side: security level, keygen ms, key size bytes | ✅ Implemented | `../pqc-control-tower/src/pqc_benchmark.py` |
| M4-S12 | **Cryptographic Inventory & CBOM** | Scan org's certs/keys; classify quantum-vulnerable; generate migration roadmap | ✅ Implemented | `../pqc-control-tower/src/crypto_inventory.py` |

---

## Module 5 — Applications & Future Trends

| # | Scenario | Demo Pitch | Status | File |
|---|----------|-----------|--------|------|
| M5-S1 | **Quantum Digital Signatures (QDS)** | One-time quantum signatures; recipient can verify, forger cannot | ✅ Implemented | `module5-applications/src/quantum_digital_signatures.py` |
| M5-S2 | **Quantum Authentication Protocol** | Identity verification using shared quantum states; replay-attack resistant | ✅ Implemented | `module5-applications/src/quantum_authentication.py` |
| M5-S3 | **Quantum-Resistant Blockchain** | Hash-based Merkle tree with SPHINCS+ signatures; show post-quantum TX signing | ✅ Implemented | `module5-applications/src/quantum_resistant_blockchain.py` |
| M5-S4 | **Trusted Relay QKD Network** | Multi-hop QKD: Alice→Relay→Bob; key relay protocol; security assumptions | ✅ Implemented | `module5-applications/src/trusted_relay_network.py` |
| M5-S5 | **Micius Satellite QKD Case Study** | China's satellite QKD: 1,200 km ground-to-satellite; QBER < 4%; key rate | ✅ Implemented | `module5-applications/src/micius_case_study.py` |
| M5-S6 | **Quantum Secure Cloud Computing** | Encrypt data with ML-KEM before cloud upload; decrypt on retrieval | ✅ Implemented | `module5-applications/src/quantum_secure_cloud.py` |
| M5-S7 | **Secure Multi-Party Computation (SMPC)** | Multiple parties compute on encrypted data; no party sees raw inputs | ✅ Implemented | `module5-applications/src/smpc_demo.py` |
| M5-S8 | **Quantum Internet Stack Demo** | Layer model: physical (QKD) → link → network → transport; qubit routing | ✅ Implemented | `module5-applications/src/quantum_internet_stack.py` |
| M5-S9 | **PQC Migration Roadmap Generator** | Input: org's crypto inventory → output: prioritised P1/P2/P3 migration plan | ✅ Implemented | `../pqc-control-tower/src/migration_planner.py` |
| M5-S10 | **Quantum IDS — Intrusion Detection** | VQC classifier on network traffic (NSL-KDD); quantum vs classical F1/AUC | ✅ Implemented | `../qc-security-lab/src/quantum_ids.py` |

---

## Summary

| Module | Total Scenarios | Implemented ✅ | Partial 🔄 | Pending ❌ |
|--------|----------------|---------------|-----------|-----------|
| M1 — Foundations | 9 | 7 | 2 | 0 |
| M2 — QKD Protocols | 7 | 6 | 1 | 0 |
| M3 — Attacks | 7 | 6 | 0 | 1 |
| M4 — PQC | 12 | 12 | 0 | 0 |
| M5 — Applications | 10 | 9 | 1 | 0 |
| **TOTAL** | **45** | **40** | **4** | **1** |

---

## Build Priority for Customer Demos

### P0 — High-Impact, Short Build (build next)
- M1-S4 Shor's Algorithm (RSA threat justification — essential for any PQC sales pitch)
- M1-S5 Grover's Algorithm (AES key-length argument)
- M2-S3 B92 Protocol (course CO3 — Qiskit implementation)
- M2-S4 E91 Protocol (course CO3 — entanglement-based, visually impressive)
- M3-S1 Intercept-Resend Attack (best live demo — shows QKD security visually)
- M3-S5 QRNG (quick win — 20 lines of Qiskit, high audience impact)

### P1 — Medium Complexity
- M2-S2 BB84 Privacy Amplification
- M3-S2 PNS Attack
- M4-S5 LWE Demo
- M4-S10 Hybrid PQC TLS
- M5-S1 Quantum Digital Signatures
- M5-S3 Quantum-Resistant Blockchain

### P2 — Advanced / Research-Level
- M2-S5 CV-QKD
- M3-S6 MDI-QKD
- M4-S6 NTRU, M4-S7 McEliece, M4-S8 BIKE/HQC
- M5-S4 Trusted Relay Network
- M5-S7 SMPC
