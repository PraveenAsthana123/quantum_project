# qc-cryptography-module

NIST-tested cryptography primitives with Known Answer Tests (KATs) covering quantum key
distribution (QKD) protocols, post-quantum cryptography (PQC) algorithms, quantum attack
simulations, and quantum information primitives.

## Modules Included

### QKD Protocols
| Module | Protocol | Description |
|--------|----------|-------------|
| `qc01_bb84` | BB84 | Bennett-Brassard 1984 QKD |
| `qc02_e91` | E91 | Ekert 1991 entanglement-based QKD |
| `qc03_b92` | B92 | Two-state QKD protocol |
| `qc04_bbm92` | BBM92 | Entanglement-based BB84 variant |
| `qc05_mdi_qkd` | MDI-QKD | Measurement-device-independent QKD |
| `qc06_tfqkd` | TF-QKD | Twin-field QKD (long-distance) |
| `qc07_cvqkd` | CV-QKD | Continuous-variable QKD |
| `qc08_sarg04` | SARG04 | Side-channel resistant QKD |

### NIST PQC Standards (FIPS 203/204/205)
| Module | Algorithm | Standard | Type |
|--------|-----------|----------|------|
| `qc09_ml_kem` | ML-KEM | FIPS 203 | Key Encapsulation |
| `qc10_ml_dsa` | ML-DSA | FIPS 204 | Digital Signature |
| `qc11_slh_dsa` | SLH-DSA | FIPS 205 | Hash-based Signature |
| `qc12_fn_dsa` | FN-DSA / FALCON | TBD | Lattice Signature |
| `qc13_bike_kem` | BIKE | Candidate | Code-based KEM |
| `qc14_classic_mceliece` | Classic McEliece | Candidate | Code-based KEM |

### Quantum Attack Simulations
| Module | Attack | Target |
|--------|--------|--------|
| `qc15_shors_rsa` | Shor's algorithm | RSA factoring |
| `qc16_shors_ecc` | Shor's algorithm | ECC discrete log |
| `qc17_grovers_aes` | Grover's search | AES brute force |
| `qc18_grovers_sha` | Grover's search | SHA preimage |
| `qc19_intercept_resend` | Intercept-resend | BB84 eavesdropping |
| `qc20_pns_attack` | PNS attack | Photon number splitting |

### Quantum Information Primitives
| Module | Primitive | Description |
|--------|-----------|-------------|
| `qc21_qrng` | QRNG | Quantum random number generation |
| `qc22_quantum_digital_signatures` | QDS | Quantum digital signatures |
| `qc23_quantum_secret_sharing` | QSS | Secret sharing protocols |
| `qc24_quantum_otp` | QOTP | Quantum one-time pad |

## Setup

```bash
pip install -r requirements.txt
```

## Running the Demo

```bash
python src/demo.py
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Known Answer Tests only
pytest tests/test_known_answers.py -v

# Specific module
pytest tests/test_qc_crypto.py::test_bb84_key_rate -v
```

## Generating Test Data

```bash
python src/generate_data.py
```

Generates `data/kat_vectors.csv` and `data/quantum_entropy.csv`.

## Data Format

### KAT Vectors (`data/kat_vectors.csv`)
| Column | Description |
|--------|-------------|
| `algorithm` | Protocol or algorithm name |
| `input_hex` | Hex-encoded input (seed, message, or key bits) |
| `expected_output_hex` | Expected output (key material, signature, ciphertext) |
| `test_type` | `keygen`, `sign`, `verify`, `encaps`, `decaps`, `extract` |
| `pass_fail` | `PASS` or `FAIL` |

### Quantum Entropy (`data/quantum_entropy.csv`)
| Column | Description |
|--------|-------------|
| `source` | Entropy source name (BB84, QRNG, PRNG, etc.) |
| `bit_string` | Raw bit string (up to 64 bits shown) |
| `entropy_bits` | Estimated min-entropy in bits |
| `is_quantum` | True if quantum-sourced |
| `notes` | Context and measurement notes |

## Architecture

```
src/
  qc01_bb84.py    ... qc24_quantum_otp.py   # 24 cryptography modules
  __init__.py                                # Package init
  demo.py                                    # Standalone demo (all modules)
  generate_data.py                           # KAT + entropy data generation
data/
  kat_vectors.csv                            # Known Answer Test vectors
  quantum_entropy.csv                        # Entropy source samples
tests/
  test_qc_crypto.py                          # Core module tests (qc01-qc12)
  test_qc_scenarios_13_24.py                 # Advanced module tests (qc13-qc24)
  test_known_answers.py                      # KAT verification
results/
  kat_results.json                           # Last KAT run summary
```
