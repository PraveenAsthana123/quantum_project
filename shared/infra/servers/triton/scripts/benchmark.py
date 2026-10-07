"""
benchmark.py — Triton Inference Server Benchmark
=================================================
Measures throughput (requests/sec), latency (p50/p95/p99), and GPU utilization
for each model at batch sizes 1, 16, 64, 256.

Usage:
    python benchmark.py --triton-url http://localhost:8000
    python benchmark.py --triton-url http://localhost:8000 --duration 30
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

try:
    import tritonclient.http as httpclient
except ImportError:
    raise SystemExit("tritonclient[http] is required: pip install tritonclient[http]")

try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except Exception:
    GPU_AVAILABLE = False


# ---------------------------------------------------------------------------
# GPU utilization helpers
# ---------------------------------------------------------------------------

def get_gpu_utilization() -> dict:
    """Return GPU utilization % and memory used (MB) for device 0."""
    if not GPU_AVAILABLE:
        return {"util_pct": -1, "mem_used_mb": -1}
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
    return {
        "util_pct": util.gpu,
        "mem_used_mb": mem.used // (1024 * 1024),
    }


# ---------------------------------------------------------------------------
# Single inference call helpers
# ---------------------------------------------------------------------------

def infer_xgboost(client, batch_size: int) -> float:
    """Send one inference to xgboost_fraud; return latency in ms."""
    data = np.random.rand(batch_size, 4).astype(np.float32)
    inp = httpclient.InferInput("input__0", [batch_size, 4], "FP32")
    inp.set_data_from_numpy(data)
    out = httpclient.InferRequestedOutput("output__0")

    t0 = time.perf_counter()
    client.infer("xgboost_fraud", [inp], outputs=[out])
    return (time.perf_counter() - t0) * 1000.0


def infer_vqc(client, batch_size: int) -> float:
    """Send one inference to quantum_vqc (capped at 64); return latency in ms."""
    bs = min(batch_size, 64)
    data = np.random.rand(bs, 4).astype(np.float32)
    inp = httpclient.InferInput("input__0", [bs, 4], "FP32")
    inp.set_data_from_numpy(data)
    out = httpclient.InferRequestedOutput("output__0")

    t0 = time.perf_counter()
    client.infer("quantum_vqc", [inp], outputs=[out])
    return (time.perf_counter() - t0) * 1000.0


def infer_transformer(client, batch_size: int) -> float:
    """Send one inference to transformer_ts; return latency in ms."""
    data = np.random.rand(batch_size, 32, 16).astype(np.float32)
    inp = httpclient.InferInput("input__0", [batch_size, 32, 16], "FP32")
    inp.set_data_from_numpy(data)
    out = httpclient.InferRequestedOutput("output__0")

    t0 = time.perf_counter()
    client.infer("transformer_ts", [inp], outputs=[out])
    return (time.perf_counter() - t0) * 1000.0


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

INFER_FNS = {
    "xgboost_fraud": infer_xgboost,
    "quantum_vqc": infer_vqc,
    "transformer_ts": infer_transformer,
}

BATCH_SIZES = [1, 16, 64, 256]
WARMUP_REQUESTS = 10
BENCHMARK_REQUESTS = 100


def run_benchmark(client, model_name: str, batch_size: int) -> dict:
    """
    Run WARMUP_REQUESTS warm-up requests, then BENCHMARK_REQUESTS timed requests
    sequentially. Returns latency stats and throughput.
    """
    infer_fn = INFER_FNS[model_name]

    # Warm-up
    for _ in range(WARMUP_REQUESTS):
        try:
            infer_fn(client, batch_size)
        except Exception:
            pass

    latencies = []
    for _ in range(BENCHMARK_REQUESTS):
        try:
            lat = infer_fn(client, batch_size)
            latencies.append(lat)
        except Exception as e:
            latencies.append(-1.0)

    valid = [l for l in latencies if l > 0]
    if not valid:
        return {"p50": -1, "p95": -1, "p99": -1, "throughput_rps": 0}

    valid_sorted = sorted(valid)
    p50 = statistics.median(valid_sorted)
    p95 = valid_sorted[int(len(valid_sorted) * 0.95)]
    p99 = valid_sorted[int(len(valid_sorted) * 0.99)]
    total_time_s = sum(valid) / 1000.0
    throughput_rps = len(valid) / total_time_s if total_time_s > 0 else 0

    return {
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "p99": round(p99, 2),
        "throughput_rps": round(throughput_rps, 1),
    }


# ---------------------------------------------------------------------------
# GPU utilization during concurrent load
# ---------------------------------------------------------------------------

def measure_gpu_during_load(client, model_name: str, batch_size: int, n_concurrent: int = 8) -> float:
    """Send concurrent requests and sample GPU utilization during the burst."""
    infer_fn = INFER_FNS[model_name]
    util_samples = []

    def send_request():
        infer_fn(client, batch_size)

    sampler_running = True

    def sample_gpu():
        while sampler_running:
            u = get_gpu_utilization()
            util_samples.append(u["util_pct"])
            time.sleep(0.05)

    import threading
    sampler = threading.Thread(target=sample_gpu, daemon=True)
    sampler.start()

    with ThreadPoolExecutor(max_workers=n_concurrent) as pool:
        futures = [pool.submit(send_request) for _ in range(n_concurrent * 4)]
        for f in as_completed(futures):
            pass

    sampler_running = False
    time.sleep(0.1)

    valid = [u for u in util_samples if u >= 0]
    return round(statistics.mean(valid), 1) if valid else -1.0


# ---------------------------------------------------------------------------
# Print table
# ---------------------------------------------------------------------------

def print_table(results: list):
    """
    results: list of dicts with keys:
        model, batch, p50, p95, p99, throughput_rps, gpu_util
    """
    header = (
        f"{'Model':<20} {'Batch':>6} {'p50ms':>8} {'p95ms':>8} "
        f"{'p99ms':>8} {'Req/s':>8} {'GPU%':>7}"
    )
    sep = "-" * len(header)
    print("\n" + sep)
    print(header)
    print(sep)

    for r in results:
        print(
            f"{r['model']:<20} {r['batch']:>6} {r['p50']:>8.2f} {r['p95']:>8.2f} "
            f"{r['p99']:>8.2f} {r['throughput_rps']:>8.1f} {r['gpu_util']:>6.1f}%"
        )

    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Benchmark Triton Inference Server.")
    parser.add_argument("--triton-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=BENCHMARK_REQUESTS,
                        help="Number of timed requests per model/batch combination.")
    args = parser.parse_args()

    url = args.triton_url.replace("http://", "")
    client = httpclient.InferenceServerClient(url=url, verbose=False)

    if not client.is_server_ready():
        raise SystemExit(f"Triton at {args.triton_url} is not ready. Start the server first.")

    all_results = []

    for model in ["xgboost_fraud", "quantum_vqc", "transformer_ts"]:
        if not client.is_model_ready(model):
            print(f"[warn] Model {model} is not loaded — skipping.")
            continue

        for bs in BATCH_SIZES:
            print(f"Benchmarking {model:20s} batch={bs:4d} ...", end=" ", flush=True)

            stats = run_benchmark(client, model, bs)
            gpu_util = measure_gpu_during_load(client, model, min(bs, 64))

            result = {
                "model": model,
                "batch": bs,
                "p50": stats["p50"],
                "p95": stats["p95"],
                "p99": stats["p99"],
                "throughput_rps": stats["throughput_rps"],
                "gpu_util": gpu_util,
            }
            all_results.append(result)
            print(f"p50={stats['p50']:.1f}ms  rps={stats['throughput_rps']:.1f}")

    print_table(all_results)

    # GPU summary
    gpu_info = get_gpu_utilization()
    if gpu_info["util_pct"] >= 0:
        print(f"\n[gpu] Current GPU util: {gpu_info['util_pct']}%  "
              f"Memory used: {gpu_info['mem_used_mb']} MB")


if __name__ == "__main__":
    main()
