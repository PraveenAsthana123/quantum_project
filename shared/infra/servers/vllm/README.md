# vLLM Server — Quantum Portal LLM Gateway

## Overview

vLLM serves open-source language models for the quantum portal with an **OpenAI-compatible API**,
making it a drop-in replacement for OpenAI API calls without the cost or data-privacy concerns.

Models hosted:

| Model | Quantization | GPU | VRAM | Purpose |
|-------|-------------|-----|------|---------|
| Gemma-2-9B-IT | AWQ 4-bit | L4 | ~4.5 GB | Fraud explanation (primary) |
| Llama-3.1-8B-Instruct | GPTQ 4-bit | L4 | ~4.0 GB | Quantum result summarization |
| Qwen-2.5-7B-Instruct | AWQ 4-bit | L4 | ~3.5 GB | Code generation |
| Mistral-7B-Instruct-v0.3 | GPTQ 4-bit | L4 | ~3.5 GB | General Q&A |
| Llama-3.1-70B-Instruct | FP8 | H100 (burst) | ~35 GB | Complex reasoning |

---

## How vLLM Works

### PagedAttention

vLLM's core innovation is **PagedAttention**: the KV-cache (key/value tensors for each token
in every active sequence) is stored in non-contiguous pages of GPU memory, like virtual memory
in an OS. This eliminates the fragmentation that forces traditional servers to pre-allocate a
large contiguous block per sequence, enabling:

- **Higher GPU utilization** — pages are allocated on demand, freed immediately after generation
- **Larger effective batch** — more concurrent sequences fit in the same VRAM
- **No memory waste** — unused KV slots are never allocated

### Continuous Batching

Unlike static batching (wait for a full batch before running the forward pass), vLLM uses
**continuous batching**: new requests are inserted into the running batch at each forward-pass
iteration. Sequences that finish are immediately replaced by queued requests. This gives near-linear
throughput scaling with concurrency and eliminates the head-of-line blocking problem.

### OpenAI-Compatible API

vLLM exposes the same `/v1/chat/completions` and `/v1/completions` endpoints as the OpenAI API:

```
POST http://localhost:8080/v1/chat/completions
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "gemma-2-9b",
  "messages": [{"role": "user", "content": "Explain why this transaction is fraudulent."}],
  "max_tokens": 512,
  "temperature": 0.2
}
```

Any OpenAI Python SDK call works with `base_url="http://localhost:8080/v1"`.

---

## Endpoints

| Port | Endpoint | Purpose |
|------|----------|---------|
| 8080 | `/v1/chat/completions` | Chat completion (primary) |
| 8080 | `/v1/completions` | Raw text completion |
| 8080 | `/v1/models` | List loaded models |
| 8080 | `/health` | Server health check |
| 8080 | `/metrics` | Prometheus metrics |

---

## Starting the Server

```bash
# Using docker-compose (starts Gemma-2-9B by default)
cd /mnt/deepa/quantum/shared/infra/servers/vllm
docker-compose up -d

# Or directly via script (supports model selection)
bash scripts/start_server.sh gemma-2-9b-it awq
bash scripts/start_server.sh meta-llama/Llama-3.1-8B-Instruct gptq
```

---

## Model Switching

vLLM loads one model per process. To switch models, restart with a different `--model` flag.
For multi-model serving, run multiple vLLM instances on different ports:

| Model | Port |
|-------|------|
| Gemma-2-9B (fraud explanation) | 8080 |
| Llama-3.1-8B (quantum summary) | 8081 |
| Qwen-2.5-7B (code gen) | 8082 |

A reverse proxy (nginx) routes by path prefix or `model` field.

---

## Integration — Quantum Explainer

See `scripts/quantum_explainer.py` for the integration with Triton VQC output.
The explainer takes the VQC inference result and calls vLLM to produce a structured,
human-readable fraud explanation.

---

## Prometheus Metrics

vLLM exposes metrics at `/metrics`:

- `vllm:num_requests_running` — active sequences in the engine
- `vllm:gpu_cache_usage_perc` — KV-cache utilization %
- `vllm:time_to_first_token_seconds` — TTFT histogram
- `vllm:time_per_output_token_seconds` — per-token latency
- `vllm:request_success_total` — completed requests counter

---

## Version History

- v1.0 — 2026-09-22 — Initial: Gemma-2-9B AWQ primary, 4-model config, quantum explainer integration
