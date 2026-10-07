# Quantum Attack System Lab

Simulates how quantum computers break classical cryptography.
Designed for defensive security education and interview preparation.

## What This Lab Covers

| Algorithm | Target | Quantum Impact |
|---|---|---|
| Shor's Algorithm | RSA, ECC, DH | BROKEN — 0 bits quantum security |
| Grover's Algorithm | AES, SHA, passwords | WEAKENED — effective bits halved |
| HNDL | All asymmetric | Active threat TODAY |

## Modules

| File | Topic |
|---|---|
| `src/shors_rsa_attack.py` | Factor RSA-15 step-by-step; resource tables for RSA-512 to RSA-4096 |
| `src/shors_ecc_attack.py` | ECDLP attack; P-256/secp256k1 (Bitcoin); $1.75T at risk |
| `src/grovers_attack.py` | AES-128/256 analysis; SHA threat table; bcrypt/PBKDF2/Argon2id |
| `src/hndl_attack.py` | 185 PB/month intercepted; 5 concrete HNDL scenarios; Mosca inequality |
| `src/quantum_crypto_analysis.py` | Complete threat matrix; system risk analyzer; migration priority |
| `src/quantum_attack_timeline.py` | 1994–2038 ASCII timeline; CRQC countdown; migration deadlines |
| `src/interview_quantum_attacks.py` | 10 expert Q&As, 150–200 words each |

## Usage

```bash
# Run all modules
python3 run_demo.py

# Run a single module
python3 run_demo.py --module shors_rsa
python3 run_demo.py --module hndl
python3 run_demo.py --module interview

# List available modules
python3 run_demo.py --list

# Run any module directly
python3 src/quantum_crypto_analysis.py
```

No external dependencies — Python 3.8+ standard library only.

## Key Numbers (Gidney & Ekerå 2021)

| RSA Key | Logical Qubits | Physical Qubits | CRQC Runtime |
|---|---|---|---|
| RSA-512 | 1,027 | ~1 million | ~10 minutes |
| RSA-1024 | 2,051 | ~2 million | ~1 hour |
| RSA-2048 | 4,099 | ~4 million | ~8 hours |
| RSA-4096 | 8,195 | ~16 million | ~4 days |

## CRQC Timeline

- **2029**: Optimistic (10% probability)
- **2033**: Moderate (50% probability) — primary planning assumption
- **2038**: Conservative (90% probability)

## Migration Targets (NIST 2024)

- **FIPS 203** — ML-KEM (replaces RSA/ECDH for key exchange)
- **FIPS 204** — ML-DSA (replaces ECDSA/RSA for signatures)
- **FIPS 205** — SLH-DSA (hash-based signatures, no lattice assumptions)
