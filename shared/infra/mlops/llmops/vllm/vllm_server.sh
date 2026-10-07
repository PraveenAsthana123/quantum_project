#!/usr/bin/env bash
# =============================================================================
# Quantum Portal — vLLM Server Startup Script
# Starts the vLLM OpenAI-compatible API server for local/dev/prod use.
#
# Usage:
#   ./vllm_server.sh                            # default: gemma-2-9b-it AWQ on L4
#   MODEL=llama-3.1-8b-instruct ./vllm_server.sh
#   ./vllm_server.sh --model qwen-2.5-7b-instruct --port 8081
#
# Prerequisites:
#   pip install vllm>=0.5.0
#   CUDA 12.1+, NVIDIA GPU with >=16 GB VRAM for default model
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults (all overridable via env vars or CLI flags)
# ---------------------------------------------------------------------------
MODEL="${MODEL:-google/gemma-2-9b-it}"
QUANTIZATION="${QUANTIZATION:-awq}"           # awq | gptq | fp8 | none
GPU_MEMORY_UTIL="${GPU_MEMORY_UTIL:-0.90}"    # fraction of VRAM to use
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"         # max context window in tokens
TENSOR_PARALLEL="${TENSOR_PARALLEL:-1}"        # GPUs for tensor parallelism
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"           # max concurrent sequences
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-quantum-llm}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# ---------------------------------------------------------------------------
# Argument parsing (CLI overrides env vars)
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    --model)           MODEL="$2";            shift 2 ;;
    --quantization)    QUANTIZATION="$2";     shift 2 ;;
    --port)            PORT="$2";             shift 2 ;;
    --tensor-parallel) TENSOR_PARALLEL="$2";  shift 2 ;;
    --max-model-len)   MAX_MODEL_LEN="$2";    shift 2 ;;
    --gpu-memory-util) GPU_MEMORY_UTIL="$2";  shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--model MODEL] [--quantization awq|gptq|fp8|none] [--port PORT]"
      echo "       [--tensor-parallel N] [--max-model-len N] [--gpu-memory-util 0.0-1.0]"
      exit 0 ;;
    *)
      echo "Unknown argument: $1"
      exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validate environment
# ---------------------------------------------------------------------------
if ! command -v python3 &> /dev/null; then
  echo "ERROR: python3 not found. Install Python 3.11+ and vllm."
  exit 1
fi

if ! python3 -c "import vllm" 2>/dev/null; then
  echo "ERROR: vllm not installed. Run: pip install vllm>=0.5.0"
  exit 1
fi

# GPU check (warn but don't abort — vLLM can run on CPU for testing)
if command -v nvidia-smi &>/dev/null; then
  GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | wc -l || echo 0)
  echo "Found ${GPU_COUNT} GPU(s):"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || true
else
  echo "WARNING: nvidia-smi not found. Running in CPU mode (very slow for large models)."
  GPU_COUNT=0
fi

# ---------------------------------------------------------------------------
# Select quantization strategy based on GPU
# ---------------------------------------------------------------------------
if [[ "${GPU_COUNT}" -eq 0 ]]; then
  QUANTIZATION="none"   # CPU: no quantization support via vLLM GPU kernels
fi

# H100: fp8 is the optimal choice (native fp8 tensor cores)
# L4/T4: awq reduces memory, good throughput
# A100: bfloat16 / gptq

echo ""
echo "=== vLLM Server Configuration ==="
echo "  Model:             ${MODEL}"
echo "  Quantization:      ${QUANTIZATION}"
echo "  GPU memory util:   ${GPU_MEMORY_UTIL}"
echo "  Max model length:  ${MAX_MODEL_LEN} tokens"
echo "  Tensor parallel:   ${TENSOR_PARALLEL} GPU(s)"
echo "  Max sequences:     ${MAX_NUM_SEQS}"
echo "  Port:              ${PORT}"
echo "  Served name:       ${SERVED_MODEL_NAME}"
echo "=================================="
echo ""

# ---------------------------------------------------------------------------
# Build vLLM command
# ---------------------------------------------------------------------------
VLLM_ARGS=(
  --model "${MODEL}"
  --host "${HOST}"
  --port "${PORT}"
  --gpu-memory-utilization "${GPU_MEMORY_UTIL}"
  --max-model-len "${MAX_MODEL_LEN}"
  --tensor-parallel-size "${TENSOR_PARALLEL}"
  --max-num-seqs "${MAX_NUM_SEQS}"
  --served-model-name "${SERVED_MODEL_NAME}"
  --enable-prefix-caching
  --disable-log-requests
  --uvicorn-log-level "${LOG_LEVEL}"
)

# Add quantization only if not "none"
if [[ "${QUANTIZATION}" != "none" ]]; then
  VLLM_ARGS+=(--quantization "${QUANTIZATION}")
fi

# Trust remote code only for models that require it (e.g. custom architectures)
if [[ "${TRUST_REMOTE_CODE:-false}" == "true" ]]; then
  VLLM_ARGS+=(--trust-remote-code)
fi

# HuggingFace token (for gated models like Gemma, Llama)
if [[ -n "${HUGGING_FACE_HUB_TOKEN:-}" ]]; then
  export HUGGING_FACE_HUB_TOKEN
fi

# Prometheus metrics endpoint (scraped by Prometheus server on port 8080/metrics)
VLLM_ARGS+=(--enable-metrics)

# ---------------------------------------------------------------------------
# Start server
# ---------------------------------------------------------------------------
echo "Starting vLLM server..."
exec python3 -m vllm.entrypoints.openai.api_server "${VLLM_ARGS[@]}"
