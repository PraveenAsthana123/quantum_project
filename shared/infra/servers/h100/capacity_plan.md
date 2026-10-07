# H100 Capacity Plan — 80 Active Users, 100GB Data

**Date:** 2026-09-22  
**Scenario:** Quantum portal, 100 total / 80 active users, 100GB finance/fraud data

---

## When H100 is Triggered

H100 is a **burst resource**, not always-on. It activates under 3 conditions:

| Trigger | Threshold | Action |
|---|---|---|
| L4 GPU memory | >80% for 5min | GKE scales H100 node pool: 0 → 1 node |
| User request Llama-70B | Any | Route to H100 vLLM pod |
| Batch quantum job | >500 circuits | Submit to Ray on H100 |

At 80 active users: **L4 handles all normal traffic**. H100 only wakes for burst or large model requests.

---

## H100 Workload Sizing

### LLM Inference (Llama-70B)
| Metric | Value |
|---|---|
| Model size (FP8) | ~35GB VRAM of H100's 80GB |
| Token throughput | ~1,100 tok/sec at batch=32 |
| TTFT (time to first token) | ~120ms |
| Requests at 80 users (Llama-70B) | ~1-2 req/min (complex reasoning only) |
| H100 utilization for 80 users | ~5% — very low |

**Conclusion:** At 80 active users, H100 is barely utilized. It becomes cost-relevant at >500 concurrent users requesting Llama-70B.

### Batch Quantum Circuit Execution (Ray)
| Metric | Value |
|---|---|
| Typical batch job | 1,000-10,000 VQC circuits × 1,000 shots |
| CPU time (L4 cluster) | ~15 min for 10K circuits |
| H100 time (GPU PennyLane lightning.gpu) | ~45 sec for 10K circuits (~20× faster) |
| Frequency | Weekly benchmark runs |

**Conclusion:** H100 for batch quantum is valuable for weekly benchmarks, not real-time inference.

### LLM Fine-tuning (LoRA)
| Metric | Value |
|---|---|
| Model | Llama-3.1-8B-Instruct |
| Dataset | ~100 quantum Q&A pairs (expandable) |
| H100 training time | ~3 min for 3 epochs |
| L4 training time | ~25 min for 3 epochs |
| Frequency | Monthly or when new quantum domain content added |

---

## Cost Model

| Scenario | GPU | Duration | Cost |
|---|---|---|---|
| Normal operation (80 users) | L4 × 1, 8h/day | 30 days | ~$180/month |
| Llama-70B burst requests | H100 × 1 | 10h/month | ~$295/month |
| Weekly batch quantum job | H100 × 1 | 2h/month | ~$59/month |
| Monthly fine-tuning | H100 × 1 | 0.25h/month | ~$7/month |
| **Total GPU cost** | | | **~$541/month** |

**Alert rule:** H100 spend >$500/month → Slack alert → review batch job frequency.

---

## Auto-scaling Config (GKE)

```yaml
# GKE node pool autoscaling for H100
nodePool:
  name: h100-burst
  autoscaling:
    minNodeCount: 0      # scale to zero when idle
    maxNodeCount: 2      # max 2× H100 nodes
  management:
    autoUpgrade: true
    autoRepair: true
  config:
    machineType: a3-highgpu-2g   # 2× H100 80GB
    accelerators:
      - acceleratorType: nvidia-h100-80gb
        acceleratorCount: 2
```

**Scale-up trigger:** Kubernetes HPA on `nvidia.com/gpu` pending pods > 0 for 3 minutes.  
**Scale-down:** `scaleDownUnneededTime: 10m` to avoid thrash.

---

## Decision Guide: L4 vs H100

```
New inference request arrives
         │
         ▼
Model size > 30GB? ──Yes──▶ Route to H100 pod
         │
        No
         │
         ▼
Current L4 mem > 80%? ──Yes──▶ Queue + trigger H100 scale-up
         │
        No
         │
         ▼
Route to L4 (always-on, cheaper)
```
