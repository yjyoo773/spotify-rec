#!/usr/bin/env bash
set -euo pipefail

# Defaults to a container-friendly location
DATA_DIR="${DATA_DIR:-/data}"
META_PATH="${META_PATH:-$DATA_DIR/meta.pkl}"
FEATURES_PATH="${FEATURES_PATH:-$DATA_DIR/features.npz}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"

echo "==> DATA_DIR=$DATA_DIR"
echo "==> META_PATH=$META_PATH"
echo "==> FEATURES_PATH=$FEATURES_PATH"

mkdir -p "$DATA_DIR"

need_download=0
[ -f "$META_PATH" ] || need_download=1
[ -f "$FEATURES_PATH" ] || need_download=1

if [ "$need_download" -eq 1 ]; then
  if [ -z "${ARTIFACT_BASE_URL:-}" ]; then
    echo "❌ Missing artifacts and ARTIFACT_BASE_URL is not set."
    echo "   Provide artifacts via a volume mount, or set ARTIFACT_BASE_URL to download them."
    exit 1
  fi

  echo "==> Downloading artifacts from $ARTIFACT_BASE_URL"
  curl -fsSL "$ARTIFACT_BASE_URL/meta.pkl" -o "$META_PATH"
  curl -fsSL "$ARTIFACT_BASE_URL/features.npz" -o "$FEATURES_PATH"
else
  echo "==> Artifacts present, no download needed."
fi

# Optional: quick sanity check (fast)
python - <<PY
import os
mp=os.environ.get("META_PATH"); fp=os.environ.get("FEATURES_PATH")
assert mp and os.path.exists(mp), f"Missing META_PATH {mp}"
assert fp and os.path.exists(fp), f"Missing FEATURES_PATH {fp}"
print("artifact check ok")
PY

# Start server (no --reload)
export DATA_DIR META_PATH FEATURES_PATH
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
