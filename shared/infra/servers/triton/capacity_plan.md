# Triton Inference Server — Capacity Plan
**Scenario:** 80 active users, 100 GB dataset, quantum portal production workload
**Date:** 2026-09-22

---

## 1. Request Rate Estimation

| Source | Users | Requests/min | Requests/sec |
|--------|-------|-------------|-------------|
| Fraud inference (xgboost_fraud) | 80 | 2 req/user/min | 2.67 req/s |
| Quantum VQC inference | 80 | 1 req/user/min | 1.33 req/s |
| Time-series transformer | 80 | 0.5 req/user/min | 0.67 req/s |
| **Total peak (3× burst factor)** | — | — | **~14 req/s peak** |

---

## 2. Hardware: NVIDIA L4 GPU

| Spec | Value |
|------|-------|
| GPU memory | 24 GB GDDR6 |
| FP32 performance | 30.3 TFLOPS |
| INT8 performance | 242 TOPS |
| Memory bandwidth | 300 GB/s |
| Max TDP | 72 W |
| GCP instance | `g2-standard-8` (1× L4, 8 vCPU, 32 GB RAM) |
| On-demand cost | ~$0.90/hr |

---

## 3. Per-Model Sizing

### 3.1 xgboost_fraud (FIL backend)

- **Model size on disk:** ~50 MB (100-tree ensemble)
- **GPU VRAM at runtime:** ~200 MB (FIL loads tree structures to GPU)
- **Latency per batch-1024:** <1 ms (FIL vectorised inference)
- **Throughput:** FIL can process >100K samples/sec at batch 1024 on L4
- **CPU fallback latency (KIND_CPU):** ~5 ms at batch 1024
- **Verdict:** L4 handles peak 14 req/s with >100× headroom.

### 3.2 quantum_vqc (Python backend — PennyLane simulator)

- **Backend:** CPU (KIND_CPU, 2 instances); no GPU required for 4-qubit simulator
- **Circuit depth:** ~30 gates (3 variational layers + encoding + CNOT rings)
- **Latency per sample:** ~10 ms (PennyLane default.qubit simulator)
- **Latency per batch-64:** ~640 ms (sequential circuit execution)
- **Dynamic batching delay:** 100 µs max queue — keeps latency predictable
- **Throughput ceiling (2 CPU instances):** ~200 samples/sec ≈ 3 req/sec at batch 64
- **Note:** At 1.33 req/sec demand, 2 CPU instances are sufficient.
  Scale to 4 instances for >3× growth.
- **GPU acceleration path (future):** lightning.gpu device reduces per-sample latency to ~1 ms.

### 3.3 transformer_ts (PyTorch LibTorch, GPU)

- **Model size:** ~500 MB (64 d_model, 2 encoder layers, full precision)
- **GPU VRAM:** ~1.5 GB loaded (model + activations at batch 32)
- **GPU latency (L4, FP16):** ~5 ms per batch-32
- **Throughput:** ~6,400 samples/sec at batch 128 on L4
- **Verdict:** L4 handles 0.67 req/sec with massive headroom.

---

## 4. Total VRAM Budget (1× L4, 24 GB)

| Model / Service | VRAM |
|----------------|------|
| xgboost_fraud (FIL) | 0.2 GB |
| transformer_ts (PyTorch FP16) | 1.5 GB |
| CUDA/driver/Triton overhead | 2.0 GB |
| **Total used** | **3.7 GB** |
| **Available headroom** | **20.3 GB** |

The L4 has significant unused VRAM. A second transformer model or a larger XGBoost ensemble
can be loaded without VRAM pressure.

---

## 5. Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| GPU utilization (sustained >5 min) | >70% | Add second L4 node |
| Triton queue depth | >50 pending requests | Enable autoscaler |
| VQC CPU utilization | >80% per instance | Increase KIND_CPU count to 4 |
| Active users | >200 | Move transformer_ts to H100 burst |

---

## 6. Cost Estimate

| SKU | Spec | Hours/day | Days/month | Cost/month |
|-----|------|-----------|------------|-----------|
| `g2-standard-8` (L4 GPU) | 1× L4, 8 vCPU, 32 GB | 8 | 22 | ~$158 |
| Storage (model repo) | 10 GB SSD | — | 30 | ~$2 |
| Egress | ~5 GB/month | — | — | ~$0.60 |
| **Total** | | | | **~$161/month** |

---

## 7. Conclusion

**One `g2-standard-8` L4 node** running Triton is sufficient for 80 active users with:
- xgboost_fraud: <1ms latency, >100× throughput headroom
- quantum_vqc: ~10ms latency, adequate for 1.33 req/sec
- transformer_ts: ~5ms GPU latency, adequate for 0.67 req/sec

Scale-up trigger: sustained >70% GPU utilization or >200 active users.
