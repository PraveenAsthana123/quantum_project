#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"
OBS="$ROOT/control-tower/observability"

cd "$OBS"

if docker compose version >/dev/null 2>&1; then
    sudo docker compose pull
    sudo docker compose up -d
elif command -v docker-compose >/dev/null 2>&1; then
    sudo docker-compose pull
    sudo docker-compose up -d
else
    echo "Docker Compose is not available."
    exit 1
fi

echo
echo "Prometheus: http://127.0.0.1:9090"
echo "Grafana   : http://127.0.0.1:3000"
echo "Loki      : http://127.0.0.1:3100"
