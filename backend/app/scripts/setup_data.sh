#!/usr/bin/env bash
set -euo pipefail

# Run from repo root OR from backend/. We normalize paths below.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$HERE/../../" && pwd)"
APP_DIR="$BACKEND_DIR/app"
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
RAW_DIR="${RAW_DIR:-$DATA_DIR/raw}"

DATASET_SLUG="${DATASET_SLUG:-yamaerenay/spotify-dataset-19212020-600k-tracks}"

echo "==> Using BACKEND_DIR=$BACKEND_DIR"
echo "==> Using DATA_DIR=$DATA_DIR"
echo "==> Using RAW_DIR=$RAW_DIR"
mkdir -p "$RAW_DIR"

# 1) Kaggle download (requires ~/.kaggle/kaggle.json with chmod 600)
if ! command -v kaggle >/dev/null 2>&1; then
  echo "❌ 'kaggle' CLI not found. Install with: pip install kaggle"
  exit 1
fi

echo "==> Downloading Kaggle dataset: $DATASET_SLUG"
kaggle datasets download "$DATASET_SLUG" -p "$RAW_DIR" --unzip

# 2) Convert to Parquet
echo "==> Converting CSV/JSON -> Parquet"
python "$APP_DIR/scripts/prepare_parquet.py"

# 3) Build features.npz + meta.pkl
echo "==> Building features"
python "$APP_DIR/scripts/build_features.py"

echo "✅ Data ready under $DATA_DIR"
ls -lh "$DATA_DIR" || true