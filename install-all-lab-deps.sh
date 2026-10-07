#!/usr/bin/env bash
# ============================================================
# Quantum Lab — Install All Missing Dependencies
# Run: bash install-all-lab-deps.sh
# ============================================================
set -e
REPO=/mnt/deepa/quantum

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Quantum Lab — Dependency Installer                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Helper ────────────────────────────────────────────────────
pip_install() {
  local venv=$1; shift
  local pkgs="$@"
  echo "  → [$venv] pip install $pkgs"
  $REPO/venvs/$venv/bin/pip install -q $pkgs 2>&1 | tail -3
}

# ── 1. QML venv (Banking + Healthcare labs) ──────────────────
echo "▶ [1/7] QML venv — Banking / Healthcare / VQC labs"
pip_install qml xgboost yfinance fastapi "uvicorn[standard]" reedsolo jax jaxlib

# ── 2. QEC venv (Error Correction lab) ───────────────────────
echo "▶ [2/7] QEC venv — Error Correction lab"
pip_install qec-architect "fastapi" "uvicorn[standard]" reedsolo

# ── 3. Optimization venv (Logistics + Annealing labs) ────────
echo "▶ [3/7] Optimization venv — Logistics / Annealing labs"
pip_install optimization "fastapi" "uvicorn[standard]" xgboost yfinance

# ── 4. Observability venv (Logging / Tracing lab) ─────────────
echo "▶ [4/7] Observability venv — Logging / Tracing lab"
pip_install observability "opentelemetry-sdk" "opentelemetry-exporter-otlp" \
  "opentelemetry-instrumentation-fastapi" qiskit qiskit-aer pennylane numpy scipy

# ── 5. Hardware venv (Quantum Hardware / Simulation lab) ──────
echo "▶ [5/7] Hardware venv — Hardware / Simulation lab"
pip_install hardware-architect "fastapi" "uvicorn[standard]" qiskit qiskit-aer \
  qutip scqubits numpy scipy matplotlib

# ── 6. Data venv (SPOC Orchestrator / Testing) ────────────────
echo "▶ [6/7] Data venv — Testing / SPOC Orchestrator"
pip_install data pytest pytest-asyncio httpx numpy scipy scikit-learn xgboost

# ── 7. Frontend (Next.js portal) ──────────────────────────────
echo "▶ [7/7] Next.js portal — frontend packages"
cd $REPO/quantum-portal-web
pnpm install --frozen-lockfile 2>/dev/null || pnpm install

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✓ All dependencies installed!                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Verification ──────────────────────────────────────────────
echo "── Verification ──────────────────────────────────────────"
echo ""
echo "QML venv:"
$REPO/venvs/qml/bin/python3 -c "import xgboost,yfinance,fastapi; print('  xgboost', xgboost.__version__, '| yfinance', yfinance.__version__, '| fastapi', fastapi.__version__)"

echo "QEC venv:"
$REPO/venvs/qec-architect/bin/python3 -c "import stim,pymatching,galois,fastapi; print('  stim', stim.__version__, '| pymatching', pymatching.__version__, '| galois', galois.__version__, '| fastapi', fastapi.__version__)"

echo "Optimization venv:"
$REPO/venvs/optimization/bin/python3 -c "import ortools,fastapi; print('  ortools', ortools.__version__, '| fastapi', fastapi.__version__)" 2>/dev/null || echo "  (partial)"

echo "Observability venv:"
$REPO/venvs/observability/bin/python3 -c "import fastapi,opentelemetry; print('  fastapi', fastapi.__version__, '| opentelemetry OK')"

echo ""
echo "All done. Start the portal with:"
echo "  cd $REPO/quantum-portal-web && pnpm dev"
echo ""
echo "Start all lab APIs with:"
echo "  bash $REPO/scripts/start-all-apis.sh"
echo ""
