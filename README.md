# Quantum Computing Portfolio

A full-stack quantum computing research and demonstration platform covering cryptography,
hybrid classical-quantum machine learning, and domain-specific labs across banking, finance,
healthcare, security, and logistics. Built to showcase production-grade engineering alongside
real quantum algorithm implementations.

---

## Overview

This workspace contains:

- **Five domain labs** (banking, finance, healthcare, security, logistics) with real datasets,
  measured AUC/accuracy results, and classical-vs-quantum comparisons
- **A cryptography module** with 24 implementations covering NIST post-quantum standards
  (FIPS 203/204/205), QKD protocols, and quantum attack simulations
- **A 159-page Next.js portal** on port 3030 that surfaces all labs, circuit visualizations,
  explainability views, AI governance pages, and a live RAG-backed Ollama chat interface
- **A FastAPI backend** on port 8001 with a 22-table SQLite schema, async background workers,
  Prometheus metrics, and ChromaDB RAG indexed over 55 arXiv papers
- **28 quantum research scaffolds** (q01-algorithms through q28-qml) covering hardware,
  error correction, compilers, distributed QC, and quantum machine learning
- **4 GitHub Actions CI workflows**, Docker Compose deployment, and daily backup automation

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser / Client                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP :3030
┌──────────────────────────────▼──────────────────────────────────────┐
│              Next.js 16 Portal  (quantum-portal-web/)                │
│   159 pages — labs, layers, governance, demo, circuit viz, RAG chat  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST :8001
┌──────────────────────────────▼──────────────────────────────────────┐
│              FastAPI Backend  (api/)                                  │
│  60+ endpoints · CAPABILITY_REGISTRY · async workers                 │
│  API-key auth · Prometheus /metrics · rate limiting                  │
└──────┬──────────────┬──────────────────┬────────────────────────────┘
       │              │                  │
┌──────▼──────┐ ┌─────▼──────┐ ┌────────▼────────┐
│  SQLite DB   │ │ ChromaDB   │ │  Ollama (local)  │
│  22 tables   │ │ RAG        │ │  LLM inference   │
│  migrations  │ │ 55 papers  │ │                  │
└─────────────┘ └────────────┘ └─────────────────┘

Domain Labs (Python, independent virtualenvs)
  qc-banking-lab/     qc-finance-lab/     qc-healthcare-lab/
  qc-security-lab/    qc-logistics-lab/   qc-cryptography-module/

Research Scaffolds
  q01-algorithms/ ... q28-qml/   (28 topic folders)
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+ / pnpm
- Docker + Docker Compose (for full stack)
- Ollama running locally (for RAG chat)

### Development — Portal + API

```bash
# 1. Start the API
cd /mnt/deepa/quantum/api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 2. Start the portal (separate terminal)
cd /mnt/deepa/quantum/quantum-portal-web
pnpm install
pnpm dev --port 3030

# Portal:  http://localhost:3030
# API:     http://localhost:8001
# API docs:http://localhost:8001/docs
# Metrics: http://localhost:8001/metrics
```

### Docker Compose (full stack)

```bash
cd /mnt/deepa/quantum
docker compose up --build
```

Services: `api` (:8001), `portal` (:3030), `db` (Postgres :5432), `cache` (Redis :6379).

### Running a lab

```bash
cd /mnt/deepa/quantum
source venvs/banking/bin/activate          # or finance, healthcare, etc.
python qc-banking-lab/src/quantum_fraud.py
python qc-cryptography-module/src/qc01_bb84.py
```

---

## Lab Results

All numbers below come from real Python runs against real datasets. No synthetic results.

| Lab | Algorithm | Metric | Value |
|-----|-----------|--------|-------|
| Banking / Fraud Detection | Random Forest (classical baseline) | AUC (multi-seed) | 0.9758 ± 0.0127 |
| Banking / Fraud Detection | Data leakage fix applied | Train-split-only preprocessing | confirmed |
| Finance / Options Pricing | Black-Scholes closed form | Option price | 4.5817 |
| Finance / Options Pricing | Monte Carlo (100k paths) | Option price | 4.5766 |
| Finance / Options Pricing | Quantum Amplitude Estimation | via Qiskit QAE | implemented |
| Healthcare / ECG Arrhythmia | Classical SVM | AUC (MIT-BIH) | 0.8864 |
| Healthcare / ECG Arrhythmia | VQC (quantum fallback) | AUC (MIT-BIH) | 0.7788 |
| Security / Intrusion Detection | VQC on NSL-KDD | AUC | 0.8429 |
| Security / Intrusion Detection | VQC configuration | 6 qubits, real data | confirmed |
| Logistics / VRP | QAOA + Simulated Annealing | 4-city TSP | solved |
| Cryptography | Test suite | Passing / KAT | 115 / 7 |

Dataset sources: MIT-BIH Arrhythmia (PhysioNet), NSL-KDD (network intrusion), Kaggle
credit card fraud, CBOE options data.

---

## Cryptography Module (QC-01 through QC-24)

Located at `qc-cryptography-module/src/`. 24 implementations:

| Range | Category |
|-------|----------|
| QC-01 BB84, QC-02 E91, QC-03 B92, QC-04 BBM92 | QKD Protocols |
| QC-05 MDI-QKD, QC-06 TF-QKD, QC-07 CV-QKD, QC-08 SARG04 | Advanced QKD |
| QC-09 ML-KEM-768 (FIPS 203), QC-10 ML-DSA-65 (FIPS 204) | NIST PQC Standards |
| QC-11 SLH-DSA (FIPS 205), QC-12 Falcon/FN-DSA | NIST PQC Standards |
| QC-13 BIKE-KEM, QC-14 Classic McEliece | Code-based KEM |
| QC-15 Shor's (RSA), QC-16 Shor's (ECC) | Quantum Attacks |
| QC-17 Grover's (AES), QC-18 Grover's (SHA) | Quantum Attacks |
| QC-19 Intercept-Resend, QC-20 PNS Attack | Attack Simulations |
| QC-21 QRNG, QC-22 Quantum Digital Signatures | Primitives |
| QC-23 Quantum Secret Sharing, QC-24 Quantum OTP | Primitives |

115 unit tests passing; 7 Known-Answer Tests (KAT) against NIST test vectors.

---

## Portal

**159 pages** built with Next.js 16, TypeScript, Tailwind CSS, served on port 3030.

Key sections:

| Section | Path | Description |
|---------|------|-------------|
| Home dashboard | `/` | Project overview, lab status cards |
| Domain labs | `/qc-banking-lab`, `/qc-finance-lab`, etc. | Per-lab results, circuit viz |
| 35-layer framework | `/layer/[id]` | Each of 35 QC layers with 8 tabs |
| 30 projects | `/projects/[id]` | Per-project experiment history |
| Architecture | `/architecture` | C4 diagrams, ADRs |
| AI Governance | `/ai-governance`, `/governance` | STRIDE, bias, fairness |
| Explainable AI | `/explainable-ai` | SHAP, attention maps |
| Cloud | `/cloud` | GCP/AWS/Azure deployment plans |
| Ollama RAG chat | `/ollama-bot` | Local LLM + 55-paper RAG |
| Demo hub | `/demo-hub`, `/demo` | Interactive walkthrough |
| Classical vs Quantum | `/classical-quantum` | Side-by-side comparisons |
| QML pipeline | `/qml-pipeline`, `/qml-simulation` | Variational circuit flows |
| Control tower | `/control-tower` | Operational monitoring |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, pnpm |
| Backend | FastAPI (Python), uvicorn, Pydantic v2 |
| Database | SQLite (dev) / PostgreSQL 16 (Docker), 22-table schema |
| Vector DB | ChromaDB — 55 arXiv papers indexed |
| Local LLM | Ollama (llama3 / mistral) |
| Quantum SDK | Qiskit, PennyLane, Cirq (per lab) |
| PQC | pycryptodome, liboqs-python (FIPS 203/204/205) |
| Containerization | Docker, Docker Compose (api + portal + db + cache) |
| CI | GitHub Actions (4 workflows: test, lint, domain-labs, security-scan) |
| Monitoring | Prometheus /metrics endpoint, structured logging |
| Load testing | Locust (scripts/) |
| Backup | cron 2am daily SQLite backup |
| Security | API-key auth middleware, rate limiting, injection guard, PII scanner |

---

## Testing

```bash
# Cryptography module — 115 unit tests + 7 KAT tests
cd /mnt/deepa/quantum/qc-cryptography-module
pytest src/ -v

# API tests
cd /mnt/deepa/quantum/api
pytest tests/ -v

# Domain lab smoke tests
cd /mnt/deepa/quantum
pytest qc-banking-lab/tests/ qc-finance-lab/tests/ -v

# Load test (requires running API)
cd /mnt/deepa/quantum/scripts
locust -f locustfile.py --host http://localhost:8001

# CI (GitHub Actions)
# .github/workflows/test.yml          — full test suite
# .github/workflows/lint.yml          — ruff + eslint
# .github/workflows/domain-labs.yml   — lab integration tests
# .github/workflows/security-scan.yml — bandit + npm audit
# .github/workflows/crypto-lab-demo.yml — cryptography demo run
```

---

## Folder Structure

```
quantum/
├── api/                          # FastAPI backend
│   ├── main.py                   # 60+ endpoints, CAPABILITY_REGISTRY
│   ├── database.py               # SQLite + migration runner
│   ├── schema.sql                # 22-table schema
│   ├── rag.py                    # ChromaDB RAG pipeline
│   ├── ollama_client.py          # Local Ollama integration
│   ├── security_routes.py        # Auth, rate limit, injection guard
│   ├── models.py                 # Pydantic models
│   ├── data.py                   # PROJECTS / LAYERS / CIRCUITS registry
│   └── migrations/               # Schema migration scripts
│
├── quantum-portal-web/           # Next.js 16 portal (159 pages)
│   ├── app/                      # App Router pages
│   ├── components/               # Shared UI components
│   └── lib/                      # API client, utils
│
├── qc-banking-lab/src/           # Banking / Fraud domain lab
├── qc-finance-lab/src/           # Finance / Options domain lab
├── qc-healthcare-lab/src/        # Healthcare / ECG domain lab
├── qc-security-lab/src/          # Security / IDS domain lab
├── qc-logistics-lab/src/         # Logistics / VRP domain lab
├── qc-cryptography-module/src/   # 24 crypto implementations (QC-01..QC-24)
│
├── qc-attack-lab/                # Quantum attack simulations
├── qc-pqc-migration-lab/         # PQC migration tooling
├── qc-crypto-lab/                # Additional crypto experiments
│
├── q01-algorithms/               # Research scaffolds (28 total)
├── q02-error-mitigation/
├── ...
├── q28-qml/
│
├── shared-modules/security/      # pqc_utils.py, shared security layer
├── manifests/                    # Kubernetes manifests
├── scripts/                      # Locust, backup, utility scripts
├── datasets/                     # Downloaded lab datasets
├── data/                         # Processed data artifacts
├── results/                      # Lab run outputs
├── docs/                         # Architecture docs, ADRs
├── docker-compose.yml
├── .github/workflows/            # 5 CI workflow files
└── CLAUDE.md                     # AI assistant project context
```

---

## 28 Research Scaffolds

Algorithm-level research folders for future implementation depth:

`q01-algorithms` (gate primitives) · `q02-error-mitigation` · `q03-ftqc` (fault-tolerant QC) ·
`q04-compiler` · `q05-ir-interop` · `q06-transpilation` · `q07-cloud-qpu` · `q08-distributed-qc` ·
`q09-circuit-cutting` · `q10-silicon-spin` · `q11-topological` · `q12-analog-qc` ·
`q13-control` · `q14-calibration` · `q15-readout` · `q16-ctrl-electronics` · `q17-cryogenics` ·
`q18-fabrication` · `q19-packaging` · `q20-chemistry` · `q21-many-body` · `q22-repeaters` ·
`q23-memory` · `q24-internet` · `q25-sensing` · `q26-metrology` · `q27-clocks` · `q28-qml`

---

## Deployment Notes

### Ports

| Service | Port |
|---------|------|
| Next.js portal | 3030 |
| FastAPI backend | 8001 |
| PostgreSQL | 5432 (Docker only) |
| Redis cache | 6379 (Docker only) |

### Environment Variables

```bash
QUANTUM_API_KEY=<secret>          # Leave unset for open demo mode
DATABASE_URL=postgresql://...     # Docker Compose sets this automatically
QUANTUM_DB_PATH=/data/quantum_portal.db
REDIS_URL=redis://cache:6379
NEXT_PUBLIC_API_URL=http://api:8001
```

### GitHub Actions

The repository has 5 CI workflow files under `.github/workflows/`:
`test.yml`, `lint.yml`, `domain-labs.yml`, `security-scan.yml`, `crypto-lab-demo.yml`.

Push to `main` triggers lint + test. The `domain-labs` workflow runs the Python lab
integration tests. The `security-scan` workflow runs bandit (Python) and npm audit (portal).

### Backup

A cron job at 2am daily creates a timestamped copy of `quantum_portal.db` and the ChromaDB
collection. See `scripts/` for the backup script.

---

## Status

| Component | Status |
|-----------|--------|
| FastAPI backend | Running — port 8001 |
| Next.js portal | Running — port 3030, 159 pages |
| Banking lab | Complete — AUC 0.9758 |
| Finance lab | Complete — QAE implemented |
| Healthcare lab | Complete — AUC 0.8864 / 0.7788 |
| Security lab | Complete — AUC 0.8429 |
| Logistics lab | Complete — 4-city TSP solved |
| Cryptography module | Complete — 115 tests passing |
| RAG (ChromaDB) | Active — 55 papers indexed |
| CI pipelines | 5 workflows active |
| Docker Compose | Ready for deployment |
| Research scaffolds (q01-q28) | Scaffolded — implementation ongoing |

---

*Last updated: 2026-10-01*
