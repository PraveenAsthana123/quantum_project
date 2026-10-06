# Quantum Security Portfolio

A production-grade quantum computing and post-quantum cryptography (PQC) research platform.

## Repository Structure

```
quantum_project/
├── pqc/                          # Post-Quantum Cryptography
│   └── labs/
│       ├── qc-pqc-migration-lab/     # Hybrid TLS/PKI/SSH/JWT migration (FIPS 203/204/205)
│       ├── qc-agent-pqc-lab/         # ML-DSA-65 SPIFFE identity + Zero Trust
│       ├── qc-blockchain-pqc-lab/    # PQ wallets, NTT transactions, CBDC PQC
│       ├── qc-classical-security-lab/# 32-algorithm CBOM registry, crypto-agility
│       ├── qc-finops-lab/            # QPU cost model, scheduler, FinOps dashboard
│       └── pqc-control-tower/        # 29-layer PQC control tower
│
├── quantum-modules/              # Quantum Computing Modules (Q01-Q28)
│   ├── q01-algorithms/           # Shor, Grover, VQE, QAOA
│   ├── q02-error-mitigation/     # ZNE, CDR, PEC
│   ├── q03-ftqc/ ... q28-qml/   # Full quantum stack
│
├── labs/                         # Domain & Security Labs
│   ├── security/
│   │   ├── qc-security-lab/      # Core quantum security
│   │   ├── qc-attack-lab/        # Quantum attack simulations
│   │   └── qc-cryptography-module/ # KAT-tested crypto primitives
│   └── domain/
│       ├── qc-banking-lab/       # Quantum fraud detection (97% accuracy)
│       ├── qc-finance-lab/       # Quantum options pricing
│       ├── qc-healthcare-lab/    # Quantum diabetes prediction
│       └── qc-logistics-lab/     # Quantum VRP optimization
│
├── quantum-portal-web/           # Next.js Portal (91 security pages)
├── api/                          # FastAPI backend
├── tests/                        # 444+ integration tests
└── .github/workflows/            # CI/CD
```

## PQC Standards (NIST Aug 2024)

| Standard | Algorithm | Use Case |
|---|---|---|
| FIPS 203 | ML-KEM-768 | TLS Key Exchange |
| FIPS 204 | ML-DSA-65 | JWT/PKI/SSH Signing |
| FIPS 205 | SLH-DSA-128f | Code Signing / CA Root |
| FIPS 206 | FALCON-512 | Compact Signatures |

## Portal

```bash
cd quantum-portal-web && pnpm install && pnpm dev
# → http://localhost:3000/security/pqc-playbook
```

Key pages: `/security/pqc-playbook` · `/security/pqc-interview` · `/security/pqc-migration-tracker` · `/security/quantum-architecture`
