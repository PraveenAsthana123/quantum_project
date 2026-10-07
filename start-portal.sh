#!/usr/bin/env bash
# Quantum Portal Startup Script
# Starts both the FastAPI backend (port 8001) and Next.js frontend (port 3030)
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NVM_DIR="/mnt/deepa/home-dirs/.nvm"

echo "=== Quantum Portal Startup ==="

# ── Node 20 via nvm ──────────────────────────────────────────────────────────
if [ -s "$NVM_DIR/nvm.sh" ]; then
  unset NPM_CONFIG_PREFIX
  source "$NVM_DIR/nvm.sh"
  nvm use 20 2>/dev/null || nvm install 20
  echo "Node: $(node --version)"
else
  echo "WARNING: nvm not found at $NVM_DIR — falling back to system Node"
fi

# ── Kill any stale instances ─────────────────────────────────────────────────
echo "Stopping old processes..."
pkill -f "uvicorn main:app.*8001" 2>/dev/null || true
pkill -f "next dev.*3030" 2>/dev/null || true
sleep 1

# ── Start FastAPI backend ─────────────────────────────────────────────────────
echo "Starting API (port 8001)..."
cd "$ROOT/api"
python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 > /tmp/quantum-api.log 2>&1 &
API_PID=$!
echo "  API PID=$API_PID"

# ── Start Next.js frontend ────────────────────────────────────────────────────
echo "Starting Portal (port 3030)..."
cd "$ROOT/quantum-portal-web"
pnpm dev --port 3030 > /tmp/quantum-portal.log 2>&1 &
PORTAL_PID=$!
echo "  Portal PID=$PORTAL_PID"

# ── Wait and verify ───────────────────────────────────────────────────────────
echo "Waiting for services..."
sleep 8

API_STATUS=$(curl -s --max-time 5 http://localhost:8001/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "starting...")
PORTAL_STATUS=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:3030 2>/dev/null || echo "000")

echo ""
echo "=== Status ==="
echo "  API    http://localhost:8001  → $API_STATUS"
echo "  Portal http://localhost:3030  → HTTP $PORTAL_STATUS"
echo ""
echo "Logs: /tmp/quantum-api.log | /tmp/quantum-portal.log"
echo "Stop:  pkill -f 'uvicorn main:app.*8001'; pkill -f 'next dev.*3030'"
