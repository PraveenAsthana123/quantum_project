# Quantum Security Lab

Quantum and post-quantum security algorithms on real network security data.

## Modules

| File | What it does |
|---|---|
| `src/classical_baseline.py` | RandomForest + XGBoost intrusion detection on NSL-KDD |
| `src/quantum_ids.py` | VQC-based Quantum IDS (PennyLane, 6 qubits, angle encoding) |
| `src/pqc_benchmark.py` | ML-KEM / ML-DSA / Falcon benchmark vs RSA-2048 / ECDSA-P256 |
| `src/qkd_bb84.py` | BB84 QKD simulation with/without eavesdropper (Qiskit Aer) |

## Dataset

NSL-KDD network intrusion dataset (`datasets/security/KDDTrain+.txt`):
- 41 features (numeric + categorical: protocol_type, service, flag)
- Labels: `normal` → 0, all attack types → 1 (binary)
- ~125 000 training samples; scripts cap at 20 000 for demo speed

## Quick Start

```bash
cd /mnt/deepa/quantum/qc-security-lab
pip install -r requirements.txt

python src/classical_baseline.py   # → data/classical_results.json
python src/quantum_ids.py          # → data/quantum_ids_results.json  (~5 min)
python src/pqc_benchmark.py        # → data/pqc_results.json
python src/qkd_bb84.py             # → data/qkd_results.json          (~2 min)
```

## Key Results (expected)

- **Classical RF/XGBoost**: accuracy ~99%, F1 ~0.99, AUC ~0.999
- **Q-IDS VQC (6 qubits)**: accuracy ~80–88%, F1 ~0.80–0.87 on balanced subset
- **PQC**: ML-KEM-768 keygen <0.05 ms; ML-DSA-65 sig ~3 KB vs RSA-2048 sig 256 B
- **BB84 no-Eve**: QBER ~0%, key agreement ~100% on sifted bits
- **BB84 with-Eve**: QBER ~25% (above 11% detection threshold → Eve detected)

## PQC Backend

The benchmark tries `liboqs-python` first (real lattice crypto).
If unavailable it falls back to timing stubs with accurate key sizes.

```bash
pip install liboqs-python   # for real FIPS 203/204/206 operations
```
