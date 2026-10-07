# Triton Inference Server — Quantum Portal

## Overview

NVIDIA Triton Inference Server (v24.01) hosts three production model backends for the quantum portal:

| Backend | Model | Protocol | Latency |
|---------|-------|----------|---------|
| FIL (Forest Inference Library) | `xgboost_fraud` | HTTP/gRPC | <1ms |
| Python (PennyLane VQC) | `quantum_vqc` | HTTP/gRPC | ~10ms |
| PyTorch LibTorch | `transformer_ts` | HTTP/gRPC | ~5ms GPU |

---

## Model Repository Layout

```
model_repository/
├── xgboost_fraud/
│   ├── config.pbtxt          # FIL backend config
│   └── 1/
│       └── model.json        # XGBoost trained model (cuML FIL format)
├── quantum_vqc/
│   ├── config.pbtxt          # Python backend config
│   └── 1/
│       ├── model.py          # PennyLane VQC TritonPythonModel class
│       └── weights.npy       # Trained variational parameters
└── transformer_ts/
    ├── config.pbtxt          # PyTorch LibTorch config
    └── 1/
        └── model.pt          # TorchScript-traced time-series transformer
```

---

## Endpoints

| Port | Protocol | Purpose |
|------|----------|---------|
| 8000 | HTTP/REST | Inference (`/v2/models/{name}/infer`), health (`/v2/health/ready`) |
| 8001 | gRPC | High-throughput binary inference, streaming |
| 8002 | HTTP/Prometheus | Metrics scrape (`/metrics`) — GPU util, request count, latency histograms |

### Quick inference test (HTTP):
```bash
curl -X POST http://localhost:8000/v2/models/xgboost_fraud/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "input__0",
      "shape": [1, 4],
      "datatype": "FP32",
      "data": [0.5, 1.2, -0.3, 0.8]
    }]
  }'
```

### Health check:
```bash
curl http://localhost:8000/v2/health/ready
```

---

## Dynamic Batching

Triton automatically aggregates concurrent requests into a single forward pass:

- **xgboost_fraud**: disabled (FIL handles vectorized batch internally)
- **quantum_vqc**: enabled, `max_queue_delay_microseconds: 100` — queues requests for up to 100µs before dispatching batch to PennyLane
- **transformer_ts**: enabled, preferred batch sizes `[1, 4, 16]`

---

## Starting the Server

```bash
# Using docker-compose (recommended)
cd /mnt/deepa/quantum/shared/infra/servers/triton
docker-compose up -d

# Or directly with Docker
docker run --gpus 1 -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v $(pwd)/model_repository:/models \
  nvcr.io/nvidia/tritonserver:24.01-py3 \
  tritonserver --model-repository=/models --log-verbose=1
```

---

## Loading Models

Run `scripts/load_models.py` to train and populate `model_repository/` before starting Triton:

```bash
pip install xgboost pennylane tritonclient[http]
python scripts/load_models.py --data datasets/creditcard.csv
```

---

## Prometheus / Grafana Integration

Triton exposes standard Prometheus metrics at `:8002/metrics`:

- `nv_inference_request_success` — per-model request counter
- `nv_inference_queue_duration_us` — queue latency histogram
- `nv_inference_compute_infer_duration_us` — GPU compute latency
- `nv_gpu_utilization` — GPU utilization %
- `nv_gpu_memory_used_bytes` — VRAM usage

Scrape config for `prometheus.yml`:
```yaml
- job_name: triton
  static_configs:
    - targets: ['triton:8002']
```

---

## Version History

- v1.0 — 2026-09-22 — Initial: xgboost_fraud (FIL), quantum_vqc (Python), transformer_ts (LibTorch)
