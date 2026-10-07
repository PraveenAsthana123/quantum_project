# vLLM Server — Capacity Plan
**Scenario:** 80 active users, 100 GB dataset, quantum portal production
**Date:** 2026-09-22

---

## 1. LLM Request Rate Estimation

| Action | Trigger | Requests/user/min | Total req/sec (80 users) |
|--------|---------|-------------------|--------------------------|
| Fraud explanation | Each VQC inference result | 1 req/min | 1.33 req/s |
| Quantum result summarization | End of circuit run | 0.5 req/min | 0.67 req/s |
| Code generation | Developer Q&A | 0.1 req/min | 0.13 req/s |
| General chatbot | Portal Q&A tab | 0.25 req/min | 0.33 req/s |
| **Total** | | | **~2.5 req/s** |
| **3× burst factor (peak)** | | | **~7.5 req/s** |

---

## 2. Primary Hardware: NVIDIA L4 GPU

| Spec | Value |
|------|-------|
| GPU memory | 24 GB GDDR6 |
| FP16 TFLOPS | 30.3 |
| INT8 TOPS | 242 |
| GCP instance | `g2-standard-8` (1× L4) |
| On-demand cost | $0.90/hr |
| 8h/day × 22 days | **~$158/month** |

---

## 3. Gemma-2-9B AWQ — Primary Model (Fraud Explanation)

| Metric | Value |
|--------|-------|
| Model params | 9 billion |
| AWQ 4-bit VRAM | ~4.5 GB |
| Throughput on L4 | ~80 tokens/sec at concurrency 1 |
| Throughput with continuous batching | ~600–800 tokens/sec at concurrency 32 |
| Average response length | ~150 tokens |
| Demand: 1.33 req/s × 150 tokens | 200 tokens/sec needed |
| L4 headroom | **~800 tokens/sec capacity vs 200 needed → 4× headroom** |
| TTFT (p50) | ~180 ms |
| TTFT (p95) | ~350 ms |

Conclusion: One L4 GPU running Gemma-2-9B AWQ handles 80 active users with comfortable
headroom even at 3× burst.

---

## 4. Full VRAM Budget for Multi-Model Serving

Running multiple models on a single L4 requires sequential model loading
(one model per vLLM process). Use separate ports:

| Model | VRAM (AWQ/GPTQ 4-bit) | L4 Port |
|-------|-----------------------|---------|
| Gemma-2-9B AWQ | 4.5 GB | 8080 |
| Llama-3.1-8B GPTQ | 4.0 GB | 8081 |
| Qwen-2.5-7B AWQ | 3.5 GB | 8082 |
| Mistral-7B GPTQ | 3.5 GB | 8083 |
| CUDA + vLLM overhead per process | ~2.0 GB | — |

Simultaneous multi-model serving on one L4 requires 4 separate processes =
4 × 2 GB overhead = 8 GB overhead + 15.5 GB models = **23.5 GB** — tight on a 24 GB L4.

**Recommended deployment pattern:**
- Production: Run Gemma-2-9B as the primary model (port 8080).
- On-demand: Load secondary models only when requested (model swap via restart).
- Scale-out: For simultaneous multi-model, add a second L4 node (total cost: ~$316/month).

---

## 5. Burst Tier: H100 (Llama-3.1-70B)

| Scenario | H100 Config | VRAM | Throughput |
|----------|-------------|------|-----------|
| Llama-3.1-70B FP8 | 2× H100 SXM5, TP=2 | ~35 GB | ~800 tokens/sec |
| Activation trigger | >200 concurrent users OR explicit complex-reasoning request | — | — |

**H100 cost model:**
- Cloud Run batch job or GKE node-pool scale-up: provisioned in ~3–5 min
- Hourly rate (a3-highgpu-1g): $3.30/hr
- Estimated usage: 10 hours/month (burst)
- **Monthly H100 cost: ~$33** (burst only)

---

## 6. Monthly Cost Summary

| Component | Spec | Cost/month |
|-----------|------|-----------|
| L4 node (primary vLLM) | g2-standard-8, 8h/day × 22 days | ~$158 |
| H100 burst | a3-highgpu-1g, 10h/month | ~$33 |
| Storage (HF model cache) | 50 GB SSD | ~$5 |
| Egress | ~10 GB/month | ~$1.20 |
| **Total** | | **~$197/month** |

---

## 7. Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| `vllm:gpu_cache_usage_perc` | >85% for >5 min | Add second L4 node |
| `vllm:num_requests_running` | >200 | Auto-scale via GKE |
| TTFT p95 | >2 seconds | Investigate queuing, add capacity |
| Active users | >200 | Trigger H100 burst node |
| H100 spend | >$500/month | Alert + review usage patterns |

---

## 8. Conclusion

**One L4 GPU (`g2-standard-8`)** running Gemma-2-9B at AWQ 4-bit handles the full 80-user
workload at ~$158/month with 4× throughput headroom.

H100 burst adds complex-reasoning capability at ~$33/month (10h/month burst), keeping total
LLM infrastructure cost under $200/month for the current scale.
