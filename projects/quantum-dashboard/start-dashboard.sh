#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"

exec "$ROOT/venvs/visualization/bin/panel" serve \
    "$ROOT/projects/quantum-dashboard/dashboard.py" \
    --address 127.0.0.1 \
    --port 5006 \
    --show
