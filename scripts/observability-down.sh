#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"
OBS="$ROOT/control-tower/observability"

cd "$OBS"

if docker compose version >/dev/null 2>&1; then
    sudo docker compose down
elif command -v docker-compose >/dev/null 2>&1; then
    sudo docker-compose down
else
    echo "Docker Compose is not available."
    exit 1
fi
