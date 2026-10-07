#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"

mkdir -p \
    "$ROOT/control-tower/mlflow/artifacts"

cd "$ROOT/control-tower/mlflow"

exec "$ROOT/venvs/observability/bin/mlflow" server \
    --host 127.0.0.1 \
    --port 5000 \
    --backend-store-uri "sqlite:///$ROOT/control-tower/mlflow/mlflow.db" \
    --default-artifact-root "$ROOT/control-tower/mlflow/artifacts"
