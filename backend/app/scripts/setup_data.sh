#!/usr/bin/env bash
set -euo pipefail

# Run from repo root OR backend/. We normalize paths below.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$HERE/../../" && pwd)"
APP_DIR="$BACKEND_DIR/app"

# Data dirs (overridable)
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
RAW_DIR="${RAW_DIR:-$DATA_DIR/raw}"
OUT_TRACKS="$DATA_DIR/tracks.csv"
OUT_ARTISTS="$DATA_DIR/artists.csv"

DATASET_SLUG="${DATASET_SLUG:-yamaerenay/spotify-dataset-19212020-600k-tracks}"

echo "==> Using BACKEND_DIR=$BACKEND_DIR"
echo "==> Using DATA_DIR=$DATA_DIR"
echo "==> Using RAW_DIR=$RAW_DIR"
mkdir -p "$RAW_DIR" "$DATA_DIR"

# 0) Require kaggle
if ! command -v kaggle >/dev/null 2>&1; then
  echo "❌ 'kaggle' CLI not found. Install with: pip install kaggle"
  exit 1
fi

# 1) Fetch dataset (idempotent-ish)
echo "==> Downloading Kaggle dataset: $DATASET_SLUG"
kaggle datasets download "$DATASET_SLUG" -p "$RAW_DIR" --unzip

# 2) Locate tracks/artists CSVs (or produce them)
#    Many forks of this dataset already include CSVs; if not, we can optionally convert.
echo "==> Searching for tracks.csv & artists.csv within $RAW_DIR"
FOUND_TRACKS="$(find "$RAW_DIR" -type f -iname 'tracks*.csv' | head -n 1 || true)"
FOUND_ARTISTS="$(find "$RAW_DIR" -type f -iname 'artists*.csv' | head -n 1 || true)"

if [[ -z "${FOUND_TRACKS:-}" || -z "${FOUND_ARTISTS:-}" ]]; then
  echo "⚠️  CSVs not found directly; attempting conversion via prepare_parquet.py (optional)"
  # This step is optional; keep only if your repo has a working converter.
  if [[ -f "$APP_DIR/scripts/prepare_parquet.py" ]]; then
    python "$APP_DIR/scripts/prepare_parquet.py"
    FOUND_TRACKS="$(find "$DATA_DIR" -maxdepth 2 -type f -iname 'tracks*.csv' | head -n 1 || true)"
    FOUND_ARTISTS="$(find "$DATA_DIR" -maxdepth 2 -type f -iname 'artists*.csv' | head -n 1 || true)"
  fi
fi

# 3) Fail if still missing
if [[ -z "${FOUND_TRACKS:-}" || -z "${FOUND_ARTISTS:-}" ]]; then
  echo "❌ Could not locate tracks.csv and/or artists.csv after download/conversion."
  echo "   Please ensure the dataset contains these files, or update prepare_parquet.py to emit them into $DATA_DIR."
  exit 1
fi

# 4) Normalize filenames/locations into app/data/
echo "==> Copying canonical CSVs into $DATA_DIR"
cp -f "$FOUND_TRACKS"  "$OUT_TRACKS"
cp -f "$FOUND_ARTISTS" "$OUT_ARTISTS"

# 5) Build features.npz + meta.pkl (audio-only embedding)
echo "==> Building features"
export DATA_DIR  # for the Python script
export TRACKS_CSV="$OUT_TRACKS"
export ARTISTS_CSV="$OUT_ARTISTS"
export FEATURES_PATH="$DATA_DIR/features.npz"
export META_PATH="$DATA_DIR/meta.pkl"
python "$APP_DIR/scripts/build_features.py"

# 6) Validate outputs
echo "==> Validating outputs"
[[ -s "$FEATURES_PATH" ]] || { echo "❌ Missing $FEATURES_PATH"; exit 1; }
[[ -s "$META_PATH" ]]     || { echo "❌ Missing $META_PATH"; exit 1; }

echo "✅ Data ready under $DATA_DIR"
ls -lh "$DATA_DIR" || true