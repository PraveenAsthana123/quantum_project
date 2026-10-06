# Blockchain PQC Lab — User Stories

Version: 1.0 | Date: 2026-10-06 | Lab: qc-blockchain-pqc-lab

---

## US-01 — Blockchain Developer: Post-Quantum Wallet Creation

**As a** blockchain developer building a next-generation digital asset platform,
**I want to** create wallets using ML-DSA-65 and SLH-DSA-128f instead of ECDSA,
**So that** wallet keys remain secure after cryptographically-relevant quantum computers arrive (projected 2030–2035).

**Acceptance Criteria:**
- PQWallet generates a key pair for ML-DSA-65, SLH-DSA-128f, or FALCON-512
- Public key bytes match FIPS 204/205 specifications (ML-DSA-65: 1952B, SLH-DSA-128f: 32B)
- Wallet address derived from SHA3-256(public_key) with "pq1" prefix
- Wallet creation completes in under 50 ms

---

## US-02 — Blockchain Developer: PQC Transaction Signing

**As a** blockchain developer integrating PQC into a payment rails,
**I want to** sign transactions with ML-DSA-65 and have the signature attached to the transaction payload,
**So that** validators can verify authenticity without trusting ECDSA whose security degrades to zero against a quantum adversary.

**Acceptance Criteria:**
- PQTransactionSigner.sign_transaction() returns signed dict with signature, algorithm, signer address, and timestamp
- Signature size matches FIPS 204 spec (ML-DSA-65: 3309 bytes)
- sign_transaction() runs in under 5 ms per transaction
- Signed payload is JSON-serializable for network broadcast

---

## US-03 — Digital Asset Custodian: Batch Transaction Verification

**As a** digital asset custodian processing thousands of transactions per day,
**I want to** batch-verify PQC-signed transactions and measure throughput,
**So that** I can confirm the system meets the minimum 500 tx/sec latency SLA before production rollout.

**Acceptance Criteria:**
- verify_transaction() returns verified=True/False and latency_ms
- Batch of 30 transactions verified in under 1 second
- Throughput (tx/sec) printed after batch
- Failed verifications reported individually

---

## US-04 — CBDC Architect: Token Mint and Transfer

**As a** CBDC architect at a central bank designing a digital currency pilot,
**I want to** mint tokens signed with ML-DSA-65 and transfer them between holders,
**So that** every token's provenance is cryptographically verifiable and quantum-safe from day one.

**Acceptance Criteria:**
- CBDCSystem.mint_token() creates a token with denomination, issuer, holder, and ML-DSA-65 signature
- CBDCSystem.transfer_token() re-signs the token under the new holder
- transfer_verified flag set to True on successful re-attestation
- CBDC demo prints token_id, denomination, issuer, algorithm, and verified status

---

## US-05 — Blockchain Developer: W-OTS+ Hash Chain Signatures

**As a** blockchain developer evaluating stateful hash-based signatures for light-client wallets,
**I want to** use W-OTS+ one-time signatures for transaction finality proofs,
**So that** I can demonstrate a quantum-safe alternative that depends only on hash-function security (no lattice assumptions).

**Acceptance Criteria:**
- WOTSPlusScheme.keygen() returns a key pair
- sign() and verify() work correctly (valid=True for correct message)
- Key size, signature size, and timing printed
- Quantum-safe classification confirmed (hash-based security)

---

## US-06 — Compliance Officer: Algorithm Migration Comparison

**As a** compliance officer preparing a quantum-readiness report for regulators,
**I want to** see a side-by-side table of ECDSA-P256 vs PQC alternatives with timing, key/signature sizes, and quantum security bits,
**So that** I can document why ECDSA must be replaced and by what deadline.

**Acceptance Criteria:**
- Comparison table covers ECDSA-P256, ML-DSA-65, SLH-DSA-128f, FALCON-512
- Columns: keygen_ms, sign_ms, verify_ms, key_bytes, sig_bytes, security_bits, quantum_safe
- ECDSA pq_security_bits = 0 (broken by Shor's algorithm)
- Table printable as plain text for inclusion in audit reports

---

## US-07 — Digital Asset Custodian: Synthetic Data for Audit Simulation

**As a** digital asset custodian preparing for a blockchain security audit,
**I want to** generate 500 synthetic transaction records with realistic timing and signature metadata,
**So that** I can run the audit simulation without exposing real customer transaction data.

**Acceptance Criteria:**
- generate_data.py produces transactions.csv with 500 rows
- Columns: tx_id, sender, recipient, amount_btc, algorithm, sig_size_bytes, sign_time_ms, verify_time_ms
- 98% of transactions marked confirmed=1
- Wallets span all four algorithms (ECDSA, ML-DSA-65, SLH-DSA-128f, FALCON-512)

---

## US-08 — CBDC Architect: Multi-Issuer CBDC Token Registry

**As a** CBDC architect coordinating a multi-central-bank pilot (BoC, ECB, Fed, PBoC),
**I want to** generate a realistic CBDC token registry covering multiple issuers and denominations,
**So that** cross-border settlement simulations have realistic data without using live central bank systems.

**Acceptance Criteria:**
- cbdc_tokens.csv contains 200 rows with token_id, denomination, issuer, holder, algorithm, verified
- Issuers include BoC-CBDC, ECB-CBDC, Fed-CBDC, PBoC-CBDC
- 35% of tokens have transferred=1
- 99% of tokens have verified=1
