#!/usr/bin/env bash
# start_server.sh — Start a vLLM instance for the quantum portal
# ===============================================================
# Usage:
#   bash start_server.sh [model_id] [quantization] [port]
#
# Examples:
#   bash start_server.sh
#   bash start_server.sh google/gemma-2-9b-it awq 8080
#   bash start_server.sh meta-llama/Llama-3.1-8B-Instruct gptq 8081
#   bash start_server.sh Qwen/Qwen2.5-7B-Instruct awq 8082
#
# Environment variables (override defaults):
#   HF_TOKEN       — HuggingFace token for gated repos (e.g. Llama)
#   GPU_DEVICE     — CUDA device index (default: 0)
#   MAX_MODEL_LEN  — Token context window (default: 4096)

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MODEL="${1:-google/gemma-2-9b-it}"
QUANTIZATION="${2:-awq}"
PORT="${3:-8080}"
GPU_DEVICE="${GPU_DEVICE:-0}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
HF_TOKEN="${HF_TOKEN:-}"

# Derive a short served-model name from the full HF repo path
SERVED_NAME=$(basename "${MODEL}" | tr '[:upper:]' '[:lower:]' | sed 's/_/-/g')

echo "======================================================"
echo "  vLLM Server — Quantum Portal"
echo "======================================================"
echo "  Model:        ${MODEL}"
echo "  Served as:    ${SERVED_NAME}"
echo "  Quantization: ${QUANTIZATION}"
echo "  Port:         ${PORT}"
echo "  GPU device:   ${GPU_DEVICE}"
echo "  Context len:  ${MAX_MODEL_LEN}"
echo "======================================================"

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    echo "[error] python3 not found. Install vLLM: pip install vllm"
    exit 1
fi

if ! python3 -c "import vllm" 2>/dev/null; then
    echo "[error] vllm Python package not found. Install: pip install vllm"
    exit 1
fi

# Check CUDA is available
if ! python3 -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    echo "[warn] CUDA not detected. vLLM will run in CPU mode (very slow)."
fi

# ---------------------------------------------------------------------------
# Export HF token if provided
# ---------------------------------------------------------------------------
if [[ -n "${HF_TOKEN}" ]]; then
    export HUGGING_FACE_HUB_TOKEN="${HF_TOKEN}"
    echo "[info] HuggingFace token set."
fi

export CUDA_VISIBLE_DEVICES="${GPU_DEVICE}"

# ---------------------------------------------------------------------------
# Build the vLLM command
# ---------------------------------------------------------------------------
VLLM_CMD=(
    python3 -m vllm.entrypoints.openai.api_server
    --model "${MODEL}"
    --served-model-name "${SERVED_NAME}"
    --port "${PORT}"
    --host 0.0.0.0
    --gpu-memory-utilization 0.85
    --max-model-len "${MAX_MODEL_LEN}"
    --max-num-seqs 256
    --tensor-parallel-size 1
    --dtype float16
    --enable-metrics
    --swap-space 4
)

# Add quantization flag only if not "none"
if [[ "${QUANTIZATION}" != "none" && "${QUANTIZATION}" != "" ]]; then
    VLLM_CMD+=(--quantization "${QUANTIZATION}")
fi

# ---------------------------------------------------------------------------
# Start vLLM in background
# ---------------------------------------------------------------------------
LOG_FILE="/tmp/vllm_${SERVED_NAME}_${PORT}.log"
echo "[info] Starting vLLM server. Log: ${LOG_FILE}"

nohup "${VLLM_CMD[@]}" > "${LOG_FILE}" 2>&1 &
VLLM_PID=$!
echo "[info] vLLM PID: ${VLLM_PID}"
echo "${VLLM_PID}" > "/tmp/vllm_${PORT}.pid"

# ---------------------------------------------------------------------------
# Health check loop — wait until server is ready (up to 180s)
# ---------------------------------------------------------------------------
ENDPOINT="http://localhost:${PORT}/health"
MAX_WAIT=180
ELAPSED=0
INTERVAL=5

echo "[info] Waiting for server to become ready at ${ENDPOINT} ..."
while true; do
    if curl -sf "${ENDPOINT}" > /dev/null 2>&1; then
        echo ""
        echo "[ready] vLLM server is up!"
        break
    fi

    if ! kill -0 "${VLLM_PID}" 2>/dev/null; then
        echo ""
        echo "[error] vLLM process exited unexpectedly. Check ${LOG_FILE}"
        tail -20 "${LOG_FILE}"
        exit 1
    fi

    if [[ "${ELAPSED}" -ge "${MAX_WAIT}" ]]; then
        echo ""
        echo "[timeout] Server did not become ready within ${MAX_WAIT}s."
        echo "          Check ${LOG_FILE} for errors."
        exit 1
    fi

    printf "."
    sleep "${INTERVAL}"
    ELAPSED=$((ELAPSED + INTERVAL))
done

# ---------------------------------------------------------------------------
# Print endpoint info and test prompt
# ---------------------------------------------------------------------------
echo ""
echo "======================================================"
echo "  Endpoint: http://localhost:${PORT}/v1/chat/completions"
echo "  Models:   http://localhost:${PORT}/v1/models"
echo "  Metrics:  http://localhost:${PORT}/metrics"
echo "======================================================"

echo ""
echo "[test] Sending test prompt ..."
RESPONSE=$(curl -s -X POST "http://localhost:${PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"${SERVED_NAME}\",
        \"messages\": [{\"role\": \"user\", \"content\": \"In one sentence, what is a quantum circuit?\"}],
        \"max_tokens\": 80,
        \"temperature\": 0.1
    }")

CONTENT=$(echo "${RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d['choices'][0]['message']['content'])
except Exception as e:
    print('Could not parse response:', e)
    print('Raw:', sys.stdin.read() if sys.stdin.readable() else '')
")

echo "[test response] ${CONTENT}"
echo ""
echo "[done] Server running. To stop: kill \$(cat /tmp/vllm_${PORT}.pid)"
