#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$HERE/../../" && pwd)"
META_PATH="${META_PATH:-$BACKEND_DIR/app/data/meta.pkl}"

JQ="cat"
if command -v jq >/dev/null 2>&1; then JQ="jq ."; fi

echo "→ /health"
curl -fsS "$BASE_URL/health" | bash -c "$JQ"

echo "→ /file-recs/health"
curl -fsS "$BASE_URL/file-recs/health" | bash -c "$JQ"

QUERY="${1:-blinding lights}"
echo "→ /file-recs/search?q=$QUERY"
curl -fsS "$BASE_URL/file-recs/search?q=$QUERY" | bash -c "$JQ"

if [ ! -f "$META_PATH" ]; then
  echo "❌ META_PATH not found at $META_PATH"
  exit 1
fi

TID="$(python - <<PY
import pickle, os, random
with open("${META_PATH}", "rb") as f: m = pickle.load(f)
print(random.choice(list(m.keys())))
PY
)"
echo "→ using track_id: $TID"

echo "→ /file-recs/recommend?track_id=$TID&k=10"
curl -fsS "$BASE_URL/file-recs/recommend?track_id=$TID&k=10" | bash -c "$JQ"

echo "✅ smoke OK"