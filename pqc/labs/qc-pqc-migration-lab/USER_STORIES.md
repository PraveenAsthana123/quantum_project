# PQC Migration Lab — User Stories

**Version:** 1.0  
**Date:** 2026-10-06  
**Lab:** qc-pqc-migration-lab  

---

## Overview

This document captures the 8 primary user stories for the Post-Quantum Cryptography (PQC) Migration Lab.
These stories reflect real enterprise migration use cases aligned with NIST SP 800-208, CISA PQC Migration Guidance, and CNSA 2.0 timelines.

---

## US-01: Crypto Asset Inventory (CBOM)

**As a** Chief Information Security Officer (CISO),  
**I want** a complete cryptographic asset inventory (CBOM — Cryptographic Bill of Materials)  
**so that** I know my organization's full Harvest-Now-Decrypt-Later (HNDL) exposure before a CRQC becomes available.

### Acceptance Criteria
- [ ] The system scans all enterprise assets and produces a CBOM with algorithm, key size, usage, and location fields
- [ ] Each asset is tagged with `hndl_exposure` (boolean or risk score) based on data sensitivity and retention period
- [ ] Assets using RSA-2048, ECDSA-P256, or ECDH-P256 are flagged as quantum-vulnerable
- [ ] The CBOM is exportable as CSV and JSON with at least 50 representative entries
- [ ] The pipeline runs end-to-end in under 30 seconds on a laptop
- [ ] A summary report shows total assets, quantum-vulnerable count, and assets by migration status

---

## US-02: Hybrid TLS Handshake with ML-KEM-768

**As a** Security Engineer,  
**I want** to run a hybrid TLS 1.3 handshake combining X25519 and ML-KEM-768  
**so that** I can protect in-transit data against HNDL attacks while maintaining classical fallback compatibility.

### Acceptance Criteria
- [ ] `HybridTLS13Handshake` completes `client_hello → server_hello → server_certificate → Finished` without exceptions
- [ ] The handshake uses code point `0x11EC` (X25519MLKEM768) per IETF draft-ietf-tls-ecdhe-mlkem
- [ ] ML-DSA-65 is used for server certificate authentication (no RSA/ECDSA)
- [ ] Wire sizes match published NIST/IETF benchmarks: ML-KEM-768 EK = 1184 bytes, ML-DSA-65 sig = 3309 bytes
- [ ] A hybrid combiner combines X25519 and ML-KEM-768 shared secrets into a single master secret
- [ ] The simulation completes in under 100 ms on a standard laptop

---

## US-03: ML-DSA-65 PKI Certificate Issuance

**As a** PKI Administrator,  
**I want** to issue ML-DSA-65 hybrid certificates from a PQC Certificate Authority  
**so that** I can replace RSA-2048 certificates before CRQC poses a real threat.

### Acceptance Criteria
- [ ] `PQCCA` generates a root CA with ML-DSA-65 keys (public key 1952 bytes, private key 4032 bytes)
- [ ] `issue_hybrid_certificate` returns a valid `HybridCertificate` with both classical and PQC signatures
- [ ] Certificates include standard X.509 fields: Subject, Issuer, Validity, Serial, OID (2.16.840.1.101.3.4.3.18)
- [ ] Certificate chains can be verified end-to-end
- [ ] A CRL / OCSP stub is present for revocation simulation
- [ ] Issuance completes in under 200 ms per certificate

---

## US-04: PQC SSH Key Exchange

**As a** DevOps Engineer,  
**I want** to use ML-KEM-768 + X25519 hybrid key exchange in SSH sessions  
**so that** my administrative sessions and infrastructure automation are quantum-safe from the moment of deployment.

### Acceptance Criteria
- [ ] `PQCSSHHandshake("mlkem768x25519-sha256").client_kex_init()` returns a 5-tuple without error
- [ ] `server_kex_reply` accepts a `HostKey` with ML-DSA-65 keys and returns a session key
- [ ] `client_derive_session_key` returns a 64-byte session key
- [ ] Host key verification via `_mldsa65_verify` returns `True` for an honest handshake
- [ ] The simulation correctly models SSH-2 `SSH_MSG_KEXECDH_INIT` / `SSH_MSG_KEXECDH_REPLY` message structures
- [ ] Session key length is at least 32 bytes

---

## US-05: ML-DSA-65 JWT Token Signing

**As a** Platform Engineer,  
**I want** to sign and verify JWT tokens using ML-DSA-65  
**so that** my API authentication tokens are quantum-resistant and comply with FIPS 204.

### Acceptance Criteria
- [ ] `PQCJWTSigner` accepts a `JWTKey` with algorithm `"ML-DSA-65"` and issues a valid JWT
- [ ] The token contains standard claims: `sub`, `iss`, `aud`, `iat`, `exp`, `jti`
- [ ] The header contains `alg: ML-DSA-65` and `kid` referencing the key ID
- [ ] `DualTokenIssuer` issues a token with both classical (RS256) and PQC (ML-DSA-65) signatures
- [ ] A verifier correctly rejects tampered token payloads
- [ ] Token issuance takes under 50 ms

---

## US-06: CNSA 2.0 Migration Status Reporting

**As a** Compliance Officer,  
**I want** to query CNSA 2.0 migration status per system and protocol  
**so that** I can accurately report organizational readiness to NSA, auditors, and the board.

### Acceptance Criteria
- [ ] The pipeline produces a per-protocol status: TLS / PKI / SSH / JWT / Code Signing
- [ ] Each protocol shows: current algorithm, target algorithm, migration phase (1-4), and estimated completion date
- [ ] CNSA 2.0 compliance percentage is calculated as `(migrated_assets / total_assets) × 100`
- [ ] A JSON report is generated at `results/migration_report.json` after each run
- [ ] The report includes CNSA 2030 readiness as a percentage
- [ ] The system flags any protocol that will miss the 2030 CNSA 2.0 deadline

---

## US-07: Algorithm Performance Benchmarks

**As a** Security Architect,  
**I want** side-by-side performance benchmarks for RSA-2048, ECDSA-P256, ML-KEM-768, ML-DSA-65, and SLH-DSA-128f  
**so that** I can accurately plan migration overhead and justify infrastructure upgrades to leadership.

### Acceptance Criteria
- [ ] `BenchmarkSuite` reports keygen, sign/encap, and verify/decap latency in milliseconds for each algorithm
- [ ] Key size and signature/ciphertext size are reported in bytes
- [ ] A comparison table shows the overhead multiplier: PQC latency / classical latency per operation
- [ ] Results are saved to `data/benchmark_results.csv` with columns: algorithm, operation, latency_ms, key_size_bytes, sig_size_bytes, quantum_safe
- [ ] ML-KEM-768 keygen is measured as < 1 ms (lightweight); SLH-DSA-128f sign is measured as > 30 ms (heavyweight)
- [ ] A `quantum_safe` boolean column is present in all benchmark results

---

## US-08: Step-by-Step Migration Guide per Protocol

**As a** Developer,  
**I want** a step-by-step migration guide for each protocol (TLS, PKI, SSH, JWT)  
**so that** I can implement PQC changes in my service without relying on tribal knowledge or reverse-engineering the simulation code.

### Acceptance Criteria
- [ ] `Stage7AlgorithmSelection` generates per-asset migration steps as a list of ordered action strings
- [ ] Each step references the relevant NIST/IETF document (e.g., FIPS 204, FIPS 203, draft-ietf-tls-ecdhe-mlkem)
- [ ] Migration steps cover: dependency audit, test environment setup, hybrid mode rollout, monitoring, classical deprecation
- [ ] The layer migration plan (`layer_migration_plan.py`) maps each of the 29 cryptographic layers to a target PQC algorithm with rationale
- [ ] A human-readable migration timeline JSON is available at `data/migration_timeline.json`
- [ ] Interview prep questions (`interview_prep.py`) cover each protocol's PQC migration rationale

---

*End of User Stories — qc-pqc-migration-lab v1.0*
