# Classical Security Lab

**Part of the Quantum Computing Portfolio** | `/mnt/deepa/quantum/qc-classical-security-lab/`

This lab demonstrates the **OLD / PRE-PQC security system** — the classical cryptographic protocols currently deployed across all 29 network and security layers. It exists as the "before" side of the PQC (Post-Quantum Cryptography) migration story.

---

## What This Lab Shows

| Scenario | What It Demonstrates |
|---|---|
| `pki` | RSA-2048 and ECDSA P-256 key generation, signing, verification, X.509 certificate chain |
| `tls` | TLS 1.3 handshake simulation: ECDHE key exchange, ECDSA auth, AES-256-GCM, HKDF |
| `jwt` | JWT HS256 / RS256 / ES256 generation and verification, replay attack vulnerability demo |
| `ssh` | SSH-2 protocol: ECDH key exchange, ECDSA host auth, AES-256-CTR bulk, HMAC-SHA256 |
| `vpn` | IPsec/IKEv2: DH Group 14 (2048-bit), PRF-HMAC-SHA256 SKEYSEED, AES-256-CBC ESP |
| `vuln` | Quantum threat matrix — 20 algorithms rated by severity, qubits needed, timeline |
| `layers` | 29-layer security map with classical algorithms and PQC migration path per layer |

---

## Quantum Threats Demonstrated

Every scenario shows inline threat assessments:

- **Shor's algorithm** — breaks RSA, ECDSA, ECDH, DH (discrete log / integer factorization) in polynomial time. Requires cryptographically relevant quantum computer (CRQC) with ~2,330–8,192 logical qubits depending on key size.
- **Grover's algorithm** — provides quadratic speedup on symmetric key search, halving effective security (AES-128 → 64-bit). AES-256 remains acceptable.
- **HNDL (Harvest Now, Decrypt Later)** — adversaries capture classical-encrypted traffic today for decryption with a future CRQC (~2030–2035).

---

## Quick Start

```bash
# List all available scenarios
python3 run_demo.py --list

# Run a single scenario
python3 run_demo.py pki
python3 run_demo.py tls

# Run multiple scenarios
python3 run_demo.py pki tls jwt

# Run everything
python3 run_demo.py --all

# Run individual files directly
python3 src/classical_pki.py
python3 src/vulnerability_analyzer.py
python3 src/layer_security_map.py
```

---

## Dependencies

Uses only Python stdlib + `cryptography` library (already installed in the quantum lab venv):

```
cryptography >= 41.0
```

No Qiskit required. No network connections required.

---

## What This Lab Does NOT Cover

- Actual quantum circuit implementations (see `qc-security-lab/` for quantum algorithms)
- PQC algorithms (see `shared-modules/security/pqc_utils.py` for ML-KEM / ML-DSA)
- Real TLS/SSH socket connections (all simulated in-process for portfolio demonstration)

---

## File Structure

```
qc-classical-security-lab/
├── run_demo.py                    Master runner (--list / --all / scenario names)
├── README.md                      This file
└── src/
    ├── classical_pki.py           RSA-2048, ECDSA P-256, X.509 cert chain
    ├── classical_tls.py           TLS 1.3 handshake simulation
    ├── classical_jwt.py           JWT HS256 / RS256 / ES256 + replay attacks
    ├── classical_ssh.py           SSH-2 protocol simulation
    ├── classical_vpn.py           IPsec/IKEv2 VPN simulation
    ├── vulnerability_analyzer.py  Quantum threat matrix (20 algorithms)
    └── layer_security_map.py      29-layer security map
```

---

## Portfolio Context

This lab is the **classical baseline** in a migration story:

```
Classical Security (this lab)
    ↓  [Quantum threat: Shor's breaks RSA/ECDSA/ECDH/DH]
PQC Migration
    ↓  [NIST FIPS 203 / 204 / 205 — 2024]
Post-Quantum Security (qc-security-lab/)
```

The vulnerability analyzer and layer map provide the architecture assessment
a Principal Security Engineer would present before proposing PQC migration.
