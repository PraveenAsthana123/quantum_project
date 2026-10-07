"""
benchmark.py — vLLM Model Benchmark for the Quantum Portal
===========================================================
Measures per-model:
  - Tokens/sec throughput at concurrency levels 1, 8, 32, 80
  - TTFT (time to first token) distribution
  - GPU VRAM used per model
  - Estimated cost per 1K output tokens

Usage:
    python benchmark.py --base-url http://localhost:8080 --model gemma-2-9b
    python benchmark.py --base-url http://localhost:8080 --model gemma-2-9b \
                        --concurrency 1 8 32 80 --prompt-tokens 128 --output-tokens 256
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import numpy as np

try:
    from openai import OpenAI
except ImportError:
    raise SystemExit("openai SDK is required: pip install openai")

try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except Exception:
    GPU_AVAILABLE = False


# ---------------------------------------------------------------------------
# Cost table — cloud GPU hourly rates (on-demand, GCP, 2026 estimate)
# ---------------------------------------------------------------------------

GPU_COST_PER_HOUR = {
    "l4": 0.90,    # g2-standard-8 with 1× L4
    "h100": 3.30,  # a3-highgpu-1g with 1× H100 80GB
}


def cost_per_1k_tokens(tokens_per_sec: float, gpu_tier: str = "l4") -> float:
    """Estimate cost per 1K output tokens based on GPU hourly rate."""
    if tokens_per_sec <= 0:
        return float("inf")
    cost_per_hour = GPU_COST_PER_HOUR.get(gpu_tier, 0.90)
    tokens_per_hour = tokens_per_sec * 3600
    return (cost_per_hour / tokens_per_hour) * 1000.0


# ---------------------------------------------------------------------------
# GPU helpers
# ---------------------------------------------------------------------------

def get_gpu_vram_used_mb() -> int:
    if not GPU_AVAILABLE:
        return -1
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
    return mem.used // (1024 * 1024)


# ---------------------------------------------------------------------------
# Benchmark: one concurrency level
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = (
    "You are a quantum computing assistant. Explain the following concept in "
    "{n_sentences} sentences: {topic}"
)

TOPICS = [
    "quantum entanglement",
    "variational quantum eigensolver",
    "quantum error correction",
    "superposition and interference",
    "quantum fraud detection",
    "PennyLane circuit execution",
    "quantum advantage over classical ML",
    "quantum circuit depth and noise",
]


def make_prompt(target_tokens: int) -> str:
    topic = TOPICS[int(time.time()) % len(TOPICS)]
    n_sentences = max(1, target_tokens // 40)
    return PROMPT_TEMPLATE.format(n_sentences=n_sentences, topic=topic)


def single_request(
    client: OpenAI,
    model: str,
    prompt: str,
    max_tokens: int,
    stream: bool = True,
) -> dict:
    """
    Send one completion request and return timing metrics.
    Uses streaming to measure TTFT accurately.
    """
    t_start = time.perf_counter()
    t_first_token = None
    total_tokens = 0

    if stream:
        stream_resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.1,
            stream=True,
        )
        for chunk in stream_resp:
            if t_first_token is None:
                t_first_token = time.perf_counter()
            delta = chunk.choices[0].delta.content if chunk.choices else ""
            if delta:
                total_tokens += len(delta.split())  # approximate
    else:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        t_first_token = time.perf_counter()
        total_tokens = resp.usage.completion_tokens if resp.usage else max_tokens

    t_end = time.perf_counter()

    ttft_ms = (t_first_token - t_start) * 1000.0 if t_first_token else -1.0
    total_ms = (t_end - t_start) * 1000.0
    tokens_per_sec = (total_tokens / ((t_end - t_start))) if (t_end - t_start) > 0 else 0.0

    return {
        "ttft_ms": ttft_ms,
        "total_ms": total_ms,
        "tokens_per_sec": tokens_per_sec,
        "total_tokens": total_tokens,
    }


def benchmark_concurrency(
    client: OpenAI,
    model: str,
    concurrency: int,
    n_requests: int,
    prompt_tokens: int,
    output_tokens: int,
) -> dict:
    """
    Run n_requests at the given concurrency level.
    Returns aggregate throughput and latency stats.
    """
    prompt = make_prompt(prompt_tokens)
    results = []
    errors = 0

    t_wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(single_request, client, model, prompt, output_tokens, True)
            for _ in range(n_requests)
        ]
        for future in as_completed(futures):
            try:
                r = future.result()
                results.append(r)
            except Exception as e:
                errors += 1

    t_wall_end = time.perf_counter()
    wall_time_s = t_wall_end - t_wall_start

    if not results:
        return {
            "concurrency": concurrency,
            "throughput_tokens_sec": 0,
            "ttft_p50_ms": -1,
            "ttft_p95_ms": -1,
            "ttft_p99_ms": -1,
            "errors": errors,
        }

    all_ttft = sorted([r["ttft_ms"] for r in results if r["ttft_ms"] > 0])
    total_tokens_generated = sum(r["total_tokens"] for r in results)
    throughput = total_tokens_generated / wall_time_s if wall_time_s > 0 else 0

    def percentile(lst, p):
        if not lst:
            return -1
        idx = int(len(lst) * p / 100)
        return lst[min(idx, len(lst) - 1)]

    return {
        "concurrency": concurrency,
        "throughput_tokens_sec": round(throughput, 1),
        "ttft_p50_ms": round(percentile(all_ttft, 50), 1),
        "ttft_p95_ms": round(percentile(all_ttft, 95), 1),
        "ttft_p99_ms": round(percentile(all_ttft, 99), 1),
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Print table
# ---------------------------------------------------------------------------

def print_table(model_name: str, gpu_tier: str, vram_mb: int, rows: list):
    print(f"\nModel: {model_name}  |  VRAM used: {vram_mb} MB  |  GPU tier: {gpu_tier}")

    header = (
        f"{'Concurrency':>12} {'Tok/sec':>10} {'TTFT p50':>10} {'TTFT p95':>10} "
        f"{'TTFT p99':>10} {'$/1K tok':>10} {'Errors':>8}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)

    for r in rows:
        c_per_1k = cost_per_1k_tokens(r["throughput_tokens_sec"], gpu_tier)
        print(
            f"{r['concurrency']:>12} {r['throughput_tokens_sec']:>10.1f} "
            f"{r['ttft_p50_ms']:>10.1f} {r['ttft_p95_ms']:>10.1f} "
            f"{r['ttft_p99_ms']:>10.1f} {c_per_1k:>10.5f} {r['errors']:>8}"
        )
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Benchmark vLLM models for the quantum portal.")
    parser.add_argument("--base-url", default="http://localhost:8080/v1")
    parser.add_argument("--model", default="gemma-2-9b")
    parser.add_argument("--concurrency", nargs="+", type=int, default=[1, 8, 32, 80])
    parser.add_argument("--requests-per-level", type=int, default=40,
                        help="Number of requests to send per concurrency level.")
    parser.add_argument("--prompt-tokens", type=int, default=128)
    parser.add_argument("--output-tokens", type=int, default=256)
    parser.add_argument("--gpu-tier", default="l4", choices=["l4", "h100"])
    args = parser.parse_args()

    client = OpenAI(base_url=args.base_url, api_key="no-key")

    # Verify the model is available
    try:
        models = client.models.list()
        available = [m.id for m in models.data]
        print(f"[info] Available models: {available}")
        if args.model not in available:
            print(f"[warn] Model '{args.model}' not found in available models. Proceeding anyway.")
    except Exception as e:
        print(f"[warn] Could not list models: {e}")

    vram_before = get_gpu_vram_used_mb()

    # Warm-up
    print(f"[warmup] Sending 3 warm-up requests to {args.model} ...")
    for _ in range(3):
        try:
            single_request(client, args.model, make_prompt(64), 64, stream=False)
        except Exception:
            pass

    vram_after_warmup = get_gpu_vram_used_mb()
    print(f"[gpu] VRAM before warmup: {vram_before} MB  |  after warmup: {vram_after_warmup} MB")

    rows = []
    for c in args.concurrency:
        print(f"[bench] Concurrency={c:3d}  n={args.requests_per_level} requests ...", end=" ", flush=True)
        result = benchmark_concurrency(
            client=client,
            model=args.model,
            concurrency=c,
            n_requests=args.requests_per_level,
            prompt_tokens=args.prompt_tokens,
            output_tokens=args.output_tokens,
        )
        rows.append(result)
        print(f"tok/sec={result['throughput_tokens_sec']:.1f}  ttft_p50={result['ttft_p50_ms']:.1f}ms")

    print_table(args.model, args.gpu_tier, vram_after_warmup, rows)

    # Summary recommendation
    peak_row = max(rows, key=lambda r: r["throughput_tokens_sec"])
    print(f"\n[summary] Peak throughput: {peak_row['throughput_tokens_sec']} tok/sec "
          f"@ concurrency={peak_row['concurrency']}")
    c_per_1k = cost_per_1k_tokens(peak_row["throughput_tokens_sec"], args.gpu_tier)
    print(f"[summary] Estimated cost: ${c_per_1k:.5f} per 1K output tokens "
          f"on {args.gpu_tier.upper()} (${GPU_COST_PER_HOUR[args.gpu_tier]}/hr)")


if __name__ == "__main__":
    main()
