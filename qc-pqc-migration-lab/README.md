# PQC Migration Lab

Post-Quantum Cryptography migration simulation suite for a quantum computing portfolio.
Demonstrates the complete enterprise transition from classical to quantum-safe cryptography.

## What it covers

| Module | What it simulates |
|--------|-------------------|
| `pqc_pki.py` | ML-DSA-65 (FIPS 204) certificate signing, hybrid X.509v3, RSA vs ML-DSA benchmarks |
| `pqc_tls.py` | Hybrid TLS 1.3: X25519+ML-KEM-768 KEX + ML-DSA-65 auth (IETF draft-ietf-tls-hybrid-design) |
| `pqc_jwt.py` | RS256 → ML-DSA-65 JWT migration; dual-token issuer; token size comparison |
| `pqc_ssh.py` | PQ SSH: sntrup761x25519 KEX + ML-DSA-65 host keys; known_hosts migration |
| `migration_pipeline.py` | 7-stage CBOM-driven migration pipeline with quantum risk scoring |
| `monitoring_dashboard.py` | 29-layer migration tracker with FIPS 140-3 / CNSA 2.0 compliance checks |
| `benchmarking.py` | Published NIST SUPERCOP benchmark data for all classical + PQC algorithms |
| `interview_prep.py` | 20 deep Q&As (10 old system + 10 new) with per-layer old/new perspective |

## Quick start

```bash
cd /mnt/deepa/quantum/qc-pqc-migration-lab
python3 run_demo.py          # run all modules in sequence

# or individual modules:
python3 src/pqc_pki.py
python3 src/benchmarking.py
python3 src/migration_pipeline.py
python3 src/interview_prep.py
```

No dependencies beyond Python 3.8+ stdlib. All cryptography is simulated with realistic
sizes and timings from published NIST benchmarks — no `liboqs` required.

## Standards covered

- **FIPS 203** — ML-KEM (August 2024)
- **FIPS 204** — ML-DSA (August 2024)  
- **FIPS 205** — SLH-DSA (August 2024)
- **NSA CNSA 2.0** (2022) — ML-KEM-1024 + ML-DSA-87 + SLH-DSA-256s
- **RFC 9370** — IKEv2 PQC Additional Key Exchange
- **IETF draft-ietf-tls-hybrid-design** — TLS 1.3 hybrid KEX
- **IETF draft-ietf-tls-ecdhe-mlkem** — X25519+ML-KEM-768 (0x11EC)
- **NIST SP 800-208** — Stateful hash-based signatures
- **NIST IR 8547** — CBOM for PQC inventories
- **CycloneDX 1.4** — CBOM schema

## Key PQC sizes (ML-DSA-65, FIPS 204 Level 3)

| Item | Size |
|------|------|
| Public key | 1,952 bytes |
| Private key | 4,032 bytes |
| Signature | 3,309 bytes |
| OID | 2.16.840.1.101.3.4.3.18 |
