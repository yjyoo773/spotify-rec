#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$HERE/../../" && pwd)"
APP_DIR="$BACKEND_DIR/app"

DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
META_PATH="${META_PATH:-$DATA_DIR/meta.pkl}"
FEATURES_PATH="${FEATURES_PATH:-$DATA_DIR/features.npz}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "==> DATA_DIR=$DATA_DIR"
echo "==> META_PATH=$META_PATH"
echo "==> FEATURES_PATH=$FEATURES_PATH"

# Ensure deps exist in THIS python
python - <<'PY'
import sys
for m in ("fastapi","uvicorn"):
    __import__(m)
print("deps ok")
PY

cd "$BACKEND_DIR"
DATA_DIR="$DATA_DIR" META_PATH="$META_PATH" FEATURES_PATH="$FEATURES_PATH" \
RELOAD="${RELOAD:-0}"
EXTRA_ARGS=()
if [ "$RELOAD" = "1" ]; then EXTRA_ARGS+=(--reload); fi

python -m uvicorn app.main:app --host "$HOST" --port "$PORT" "${EXTRA_ARGS[@]}"
