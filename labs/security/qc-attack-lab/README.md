# QC Attack Lab — Quantum Security Attack Simulation

Educational attack simulation lab for quantum security portfolio.

**Purpose:** Defensive security education. Simulates classical and quantum-era
attacks so defenders understand and prevent them. All code is theoretical/educational only.

## Modules

| File | Description |
|------|-------------|
| `src/classical_attacks.py` | RSA factoring, timing side-channel, Bleichenbacher, birthday, MITM, JWT replay |
| `src/quantum_attacks.py` | Shor's (RSA/ECC), Grover's (AES/SHA-256), HNDL, AI-assisted crypto attacks |
| `src/ai_attacks.py` | FGSM adversarial, model extraction, data poisoning, prompt injection, model inversion |
| `src/attack_detection.py` | 24-hour traffic simulation with timing/HNDL/cert/JWT/side-channel detectors |
| `src/defense_playbook.py` | Per-attack: immediate → 30-day → PQC migration + compliance mapping |
| `src/interview_attack_prep.py` | 26 Q&As: classical crypto, Shor's/Grover's, HNDL, AI attacks |

## Run

```bash
cd /mnt/deepa/quantum/qc-attack-lab
python run_demo.py          # full suite

# Individual modules
python src/classical_attacks.py
python src/quantum_attacks.py
python src/ai_attacks.py
python src/attack_detection.py
python src/defense_playbook.py
python src/interview_attack_prep.py
```

**Requirements:** Python 3.10+ stdlib only (numpy optional, graceful fallback).
