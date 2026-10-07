# H100 GPU Server — Quantum Portal

NVIDIA H100 SXM5 80GB HBM3 — burst GPU for large model inference, fine-tuning, and batch quantum circuit execution.

## When to Use H100 vs L4

| Workload | L4 (24GB, always-on) | H100 (80GB, burst only) |
|---|---|---|
| Gemma-2-9B AWQ | ✅ fits in 4.5GB | overkill |
| Llama-3.1-8B GPTQ | ✅ fits in 4GB | overkill |
| Llama-3.1-70B FP8 | ❌ needs 35GB | ✅ required |
| LoRA fine-tuning | ❌ too slow | ✅ 10× faster |
| Batch QPU simulation | ✅ CPU Ray | ✅ GPU Ray (faster) |
| >200 concurrent users | ❌ bottleneck | ✅ scale-out |

## Hardware Specs
- GPU memory: 80GB HBM3
- Memory bandwidth: 3.35 TB/s
- FP8 Tensor Cores: 3,958 TFLOPS
- NVLink 4.0: 900 GB/s (multi-GPU tensor parallel)
- PCIe Gen5 host bandwidth: 128 GB/s

## Deployment Model (GKE)
- **Not always-on** — on-demand node pool (`a3-highgpu-2g` = 2× H100)
- Auto-scaling: 0 nodes at idle → scale up when L4 memory util >80% for 5min
- Cost: ~$33/hour on-demand; ~$330/month at 10h/month burst

## Folder Structure
```
h100/
├── README.md          # This file
├── config/
│   ├── ray_cluster.yaml    # Ray on GKE with H100
│   └── llm_h100.yaml       # vLLM config for Llama-70B on H100
└── scripts/
    ├── ray_quantum_batch.py # Batch VQC circuit execution via Ray
    ├── finetune_llm.py      # LoRA fine-tune on quantum domain Q&A
    └── gpu_benchmark.py     # Compare L4 vs H100 on key workloads
```

## Quick Start
```bash
# Start Ray cluster on H100
ray up config/ray_cluster.yaml

# Submit batch quantum job
python scripts/ray_quantum_batch.py --dataset data/fraud_transactions.csv --n-samples 10000

# Fine-tune Llama-3.1-8B on quantum Q&A
python scripts/finetune_llm.py --model meta-llama/Llama-3.1-8B --output models/quantum-llama

# Benchmark L4 vs H100
python scripts/gpu_benchmark.py
```
