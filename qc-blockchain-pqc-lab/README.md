# Blockchain / Digital Asset PQC Lab

Post-quantum cryptography for blockchain and digital assets. Implements
ML-DSA-65 (FIPS 204), SLH-DSA-128f (FIPS 205), FALCON-512, W-OTS+/LMS
(SP 800-208/RFC 8554), and a PQ-safe CBDC system.

## Modules

| File | Purpose |
|---|---|
| `src/pq_wallet.py` | PQ wallet: ML-DSA-65, SLH-DSA-128f, FALCON-512 keypairs; address derivation; ECDSA comparison |
| `src/pq_transaction.py` | PQ transaction signing; batch verify; block overhead; migration path |
| `src/hash_chain_signature.py` | W-OTS+ and LMS stateful hash-based signatures |
| `src/cbdc_pqc.py` | PQ-safe CBDC mint/transfer/verify; privacy audit; BIS/FATF compliance |
| `tests/test_blockchain_pqc.py` | 24 pytest tests |

## Quick start

```bash
pip install -r requirements.txt
python src/pq_wallet.py
python src/pq_transaction.py
python src/hash_chain_signature.py
python src/cbdc_pqc.py
pytest tests/ -v
```

## Algorithms

| Algorithm | Standard | Sig (B) | PK (B) | Quantum Sec |
|---|---|---|---|---|
| ECDSA-P256 | FIPS 186-5 | 64 | 64 | 0-bit (Shor) |
| ML-DSA-65 | FIPS 204 | 3309 | 1952 | 178-bit |
| SLH-DSA-128f | FIPS 205 | 17088 | 32 | 128-bit |
| FALCON-512 | FIPS 206 draft | 666 | 897 | 128-bit |
| W-OTS+ | SP 800-208 / RFC 8554 | 2144 | 2144 | 128-bit |

## Security notes

- ML-DSA-65 signing uses real NTT polynomial arithmetic: N=256, Q=8380417, K=6, L=5
- W-OTS+ is **one-time only** — use LMSSignature for multi-message signing
- Harvest-Now-Decrypt-Later attacks are active; migration recommended by 2027
