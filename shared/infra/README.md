# Quantum Portal — Shared Infrastructure

Production-grade infrastructure for the Quantum Portal platform.
Targets: **100 concurrent users**, **100 GB finance/fraud dataset**, **30 quantum lab projects**.

---

## Folder Structure

```
shared/infra/
├── terraform/
│   ├── gcp/          GKE Autopilot, Cloud Run, Cloud SQL, Memorystore, GCS, BigQuery, KMS, VPC
│   ├── aws/          EKS, ECR, RDS PostgreSQL, ElastiCache Redis, S3, SageMaker, CloudFront, WAF
│   └── azure/        AKS, ACR, PostgreSQL Flexible, Redis Cache, Blob Storage, Azure OpenAI, Key Vault, Log Analytics
├── helm/
│   └── quantum-portal/   Helm chart: Next.js portal, FastAPI API, Worker, Redis, PostgreSQL
├── docker/
│   └── docker-compose.yml   Local dev stack: all 10 services
├── mlops/
│   ├── mlflow_config.py      MLflow experiment tracking helpers
│   └── vertex_pipeline.py    Vertex AI KFP v2 pipeline (7 steps)
├── observability/
│   ├── prometheus_config.yml  Scrape config + alert rule stubs
│   └── grafana_dashboard.json 8-panel production dashboard
└── scripts/
    └── deploy.sh              Production deploy script
```

---

## Quick Start: Local Development

Requirements: Docker >= 24, Docker Compose >= 2.20, NVIDIA Container Toolkit (optional, for Triton GPU).

```bash
# Copy environment template and fill secrets
cp docker/.env.example docker/.env

# Start all services
docker compose -f docker/docker-compose.yml up -d

# Verify health
docker compose -f docker/docker-compose.yml ps
```

| Service         | URL                        | Purpose                          |
|-----------------|----------------------------|----------------------------------|
| quantum-portal  | http://localhost:3001       | Next.js frontend                 |
| quantum-api     | http://localhost:8000       | FastAPI backend                  |
| quantum-worker  | (internal)                  | Circuit execution worker         |
| postgres        | localhost:5432              | Results + metadata DB            |
| redis           | localhost:6379              | Job queue + cache                |
| minio           | http://localhost:9000       | S3-compatible object store       |
| minio console   | http://localhost:9001       | MinIO admin UI                   |
| mlflow          | http://localhost:5000       | Experiment tracking              |
| prometheus      | http://localhost:9090       | Metrics collection               |
| grafana         | http://localhost:3000       | Dashboards (admin/admin)         |
| triton          | http://localhost:8001       | NVIDIA Triton (GPU optional)     |
| ollama          | http://localhost:11434      | Local LLM serving                |

---

## Quick Start: Cloud Deploy

### GCP (recommended)

```bash
# Authenticate
gcloud auth application-default login

# Initialise and apply Terraform
cd terraform/gcp
terraform init -backend-config=backend.conf
terraform plan -var env=prod -out prod.plan
terraform apply prod.plan

# Deploy Helm chart
./scripts/deploy.sh --env prod --cloud gcp \
  --portal-image gcr.io/PROJECT/quantum-portal:v1.0.0 \
  --api-image    gcr.io/PROJECT/quantum-api:v1.0.0 \
  --worker-image gcr.io/PROJECT/quantum-worker:v1.0.0
```

### AWS

```bash
aws sso login  # or configure ~/.aws/credentials

cd terraform/aws
terraform init -backend-config=backend.conf
terraform plan -var env=prod -var db_password=$DB_PASS -out prod.plan
terraform apply prod.plan

# Get kubeconfig for EKS
aws eks update-kubeconfig --region us-east-1 --name quantum-portal-prod

./scripts/deploy.sh --env prod --cloud aws
```

### Azure

```bash
az login

cd terraform/azure
terraform init -backend-config=backend.conf
terraform plan -var env=prod -var db_password=$DB_PASS -out prod.plan
terraform apply prod.plan

# Get kubeconfig for AKS
az aks get-credentials --resource-group rg-quantum-portal-prod --name aks-quantum-prod

./scripts/deploy.sh --env prod --cloud azure
```

---

## Deploy Script Reference

```
./scripts/deploy.sh [options]

Options:
  --env prod|staging|dev    Deployment environment (default: prod)
  --cloud gcp|aws|azure     Target cloud (default: gcp)
  --portal-image IMG        Next.js portal image tag
  --api-image IMG           FastAPI API image tag
  --worker-image IMG        Worker image tag
  --skip-terraform          Skip Terraform init/plan/apply
  --skip-helm               Skip Helm upgrade
  --dry-run                 Show what would happen, apply nothing
  --timeout 300s            Helm/rollout timeout (default: 300s)
  --smoke-url URL           Base URL for smoke tests
  --namespace NAME          Kubernetes namespace (default: quantum-portal)

Environment variables:
  SLACK_WEBHOOK_URL         Post success/failure notifications to Slack
```

---

## MLflow Experiment Tracking

```python
from shared.infra.mlops.mlflow_config import (
    configure_mlflow, quantum_run, log_quantum_metrics,
    QuantumRunParams, QuantumRunMetrics, QuantumModelRegistry,
)

configure_mlflow("http://mlflow:5000")

params = QuantumRunParams(
    n_qubits=8, n_layers=3, shots=1024,
    backend="aer_simulator", encoding="angle",
)
with quantum_run("quantum-fraud-detection", "vqc_run_001", params) as run:
    # ... train ...
    metrics = QuantumRunMetrics(accuracy=0.82, auc=0.88, f1=0.79,
                                 circuit_depth=24, fidelity=0.91, runtime_ms=3400)
    log_quantum_metrics(run.info.run_id, metrics)

# Promote to production if gates pass (auc>=0.75, fidelity>=0.80, acc>=0.75)
registry = QuantumModelRegistry()
version = registry.register(run_id, "quantum_weights", "quantum-fraud-vqc")
registry.promote_to_production("quantum-fraud-vqc", version.version, run_id)
```

---

## Vertex AI Pipeline

```bash
# Compile and submit the 7-step quantum ML pipeline
python mlops/vertex_pipeline.py \
  --project  quantum-portal-prod \
  --region   us-central1 \
  --pipeline-root gs://quantum-portal-prod-quantum-datasets-prod/pipelines \
  --dataset-gcs-uri gs://quantum-portal-prod-quantum-datasets-prod/fraud_data.parquet \
  --submit
```

Pipeline steps: data validation → preprocessing → VQC training → classical RF comparison → evaluation → model registration → canary deployment (10% traffic).

---

## Observability

### Import Grafana Dashboard

```bash
# Import via Grafana API
curl -X POST http://localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -u admin:$GRAFANA_PASSWORD \
  -d "{ \"dashboard\": $(cat observability/grafana_dashboard.json), \"overwrite\": true }"
```

### Prometheus Alert Rules

Copy the rule stubs from `observability/prometheus_config.yml` comments to
`/etc/prometheus/rules/quantum_alerts.yml` on your Prometheus instance and reload:

```bash
curl -X POST http://localhost:9090/-/reload
```

Critical alerts defined:

| Alert | Threshold | Severity |
|---|---|---|
| QuantumCircuitFidelityLow | fidelity < 0.80 for 5m | warning |
| QuantumAPILatencyHigh | p99 > 2s for 3m | critical |
| GPUUtilizationHigh | GPU util > 90% for 10m | warning |
| TritonInferenceErrorRate | error rate > 5% for 5m | critical |
| QuantumJobQueueDepthHigh | queue > 50 jobs for 5m | warning |
| PostgresConnectionsSaturated | connections > 85% for 5m | warning |
| QuantumAPIPodRestartLoop | > 3 restarts in 15m | critical |

---

## Cost Summary

Estimated monthly cost at 100 concurrent users + 100 GB dataset. On-demand pricing; reserved instances reduce cost 30–40%.

| Component | GCP (us-central1) | AWS (us-east-1) | Azure (eastus) |
|---|---:|---:|---:|
| Kubernetes (GKE Autopilot / EKS / AKS) | $450 | $320 | $380 |
| GPU node (T4, 1 node avg) | $200 | $150 | $230 |
| Database (PostgreSQL) | $150 | $80 | $180 |
| Cache (Redis) | $60 | $40 | $70 |
| Object Storage (100 GB) | $20 | $23 | $19 |
| CDN / Load Balancer | $80 | $35 | $80 |
| AI Services (Vertex AI / SageMaker / Azure ML) | $100 | $30 | $60 |
| Monitoring / Logging | $50 | $10 | $28 |
| **Total (est.)** | **$1,110** | **$688** | **$1,047** |

---

## Architecture Overview

```
                  ┌─────────────────────────────────────────────────┐
                  │                   Users (100)                    │
                  └──────────────────────┬──────────────────────────┘
                                         │ HTTPS
                              ┌──────────▼──────────┐
                              │  CDN / Front Door   │
                              │  (WAF / rate-limit) │
                              └──────────┬──────────┘
                                         │
                    ┌────────────────────▼─────────────────────┐
                    │            Kubernetes Cluster             │
                    │  ┌──────────┐  ┌──────────┐  ┌────────┐ │
                    │  │ quantum  │  │ quantum  │  │quantum │ │
                    │  │ -portal  │  │  -api    │  │-worker │ │
                    │  │ (Next.js)│  │ (FastAPI)│  │(Celery)│ │
                    │  └────┬─────┘  └────┬─────┘  └───┬────┘ │
                    │       │             │              │      │
                    │  ┌────▼─────────────▼──────────────▼────┐│
                    │  │           Triton / Ollama             ││
                    │  │        (GPU node pool)                ││
                    │  └───────────────────────────────────────┘│
                    └──────────┬─────────────────┬──────────────┘
                               │                 │
                    ┌──────────▼───┐   ┌──────────▼──────┐
                    │ PostgreSQL   │   │  Redis           │
                    │ (results DB) │   │  (job queue)     │
                    └──────────────┘   └─────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Object Store (GCS   │
                    │ / S3 / Blob)        │
                    │ 100 GB datasets     │
                    └─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ MLflow Tracking     │
                    │ + Model Registry    │
                    └─────────────────────┘
```

---

## Security Notes

- All inter-service traffic encrypted in transit (TLS 1.2+).
- Secrets managed via GCP Secret Manager / AWS Secrets Manager / Azure Key Vault — never in environment files in production.
- WAF rules: OWASP CRS + known-bad-inputs + rate limit (2000 req/5min/IP).
- EKS/AKS: RBAC + Azure AD / IAM for kubectl access.
- RDS/PostgreSQL: encrypted at rest (KMS), no public access, enhanced monitoring.
- ECR/ACR: image scanning on push, lifecycle policies retain last 10–20 tagged images.
- GPU nodes: tainted `nvidia.com/gpu=true:NoSchedule` — only Triton/worker pods schedule there.
