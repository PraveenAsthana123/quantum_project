# QC Crypto Lab
Quantum Cryptography demo scenarios — based on the 5-module university course syllabus.
42 scenarios across foundations, QKD protocols, attacks, PQC, and applications.

## Quick Start
```bash
# Run any scenario
python3 run_scenario.py M1-S4    # Shor's Algorithm
python3 run_scenario.py M2-S1    # BB84 QKD
python3 run_scenario.py M3-S1    # Intercept-Resend Attack
python3 run_scenario.py M4-S1    # ML-KEM Benchmark
python3 run_scenario.py M5-S3    # Quantum-Resistant Blockchain

# List all scenarios with status
python3 run_scenario.py --list

# Run all implemented scenarios
python3 run_scenario.py --all
```

## Scenario Status
See [SCENARIOS.md](SCENARIOS.md) for the full list (42 scenarios, 9 implemented, 32 pending).

## Modules
| Module | Folder | Scenarios |
|--------|--------|-----------|
| M1 — Foundations | `module1-foundations/` | Qubit, Entanglement, No-Cloning, Shor's, Grover's |
| M2 — QKD Protocols | `module2-qkd/` | BB84, B92, E91, CV-QKD, Fiber model |
| M3 — Attacks | `module3-attacks/` | Intercept-Resend, PNS, Trojan Horse, QRNG, MDI-QKD |
| M4 — PQC | `module4-pqc/` | ML-KEM, ML-DSA, LWE, NTRU, McEliece, Hybrid TLS |
| M5 — Applications | `module5-applications/` | QDS, Blockchain, Relay Network, Micius, Cloud, SMPC |
