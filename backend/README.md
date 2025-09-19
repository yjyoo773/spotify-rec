# Spotify Rec — Backend (MVP)

A lightweight, **file-backed** recommendation API you can run locally and demo in minutes.
**Pipeline**: Kaggle data → Parquet → 128-dim vectors → FastAPI routes. **No DB required**.

## What this does (at a glance)

1. Fetches the Kaggle dataset (tracks + artists).
2. Prepares it into compact Parquet files with robust parsing.
3. Builds deterministic 128-dim vectors from simple tokens (genres + year + popularity bucket).
4. Serves a FastAPI with /search and /recommend that returns similar tracks.

## Directory layout
```bash
backend/
  app/
    main.py                         # FastAPI app (search + recommend)
    recommender/
      file_backend.py               # loads vectors/meta, cosine KNN + small rerank
    scripts/
      fetch_kaggle.py               # (optional) Kaggle CLI download
      prepare_parquet.py            # CSV/JSON -> Parquet
      build_features.py             # Parquet -> features.npz + meta.pkl
      setup_data.sh                 # download + prepare + build (shell, easiest)
      run_api.sh                    # start API with correct paths (shell)
      smoke_test.sh                 # end-to-end curl smoke test (shell)
    data/                           # generated artifacts (gitignored)
      raw/                          # raw Kaggle files unzip here
      catalog.parquet               # tracks
      artist_genres.parquet         # artists + genres
      features.npz                  # vectors [N x 128]
      meta.pkl                      # {track_id: {title, artists, year, pop_bucket}}
```

All files under `app/data/` are **gitignored** (except a `.gitkeep` placeholder).

## Quickstart
0) Install Python deps
``` bash
cd backend
python -m pip install -r requirements.txt
```
1) Set up Kaggle token (one time)

* Kaggle → Profile → Account → Create New Token

* Save to:
   * macOS/Linux: ~/.kaggle/kaggle.json and chmod 600 ~/.kaggle/kaggle.json
   * Windows: %USERPROFILE%\.kaggle\kaggle.json

2) Build the data (fetch → prepare → features)
``` bash
# from repo root (or backend/) — the script handles paths
backend/app/scripts/setup_data.sh
```

3) Run the API
```bash
# from repo root (or backend/)
backend/app/scripts/run_api.sh
```

4) Smoke test (in another terminal)
``` bash
backend/app/scripts/smoke_test.sh
```

## Endpoints
### Health
``` bash
GET /health
→ { "status": "ok", "service": "spotify-rec", "mode": "file-backed" }
```

### Search (title, naive)
``` pgsql
GET /file-recs/search?q=blinding%20lights&limit=10
GET /search?q=blinding%20lights&limit=10     # alias
```

Response:
```json

{
  "query": "blinding lights",
  "items": [
    {
      "id": "0VjIjW4GlUZAMYd2vXMi3b",
      "title": "Blinding Lights",
      "artists": ["0X2BH1fck6amBIoJhDVmmJ"],
      "year": "2019",
      "pop_bucket": 9
    }
  ]
}
```
### Recommend (cosine similarity + tiny rerank)
``` bash
GET /file-recs/recommend?track_id=0VjIjW4GlUZAMYd2vXMi3b&k=20
GET /recommend?track_id=...&k=20                       # alias
```
* Accepts raw ID, spotify:track:<id>, or https://open.spotify.com/track/\
<id> (IDs normalized).
* Returns neighbors with score + minimal metadata.

Response:
```json
{
  "query_id": "0VjIjW4GlUZAMYd2vXMi3b",
  "items": [
    {"id":"...", "score":0.83, "title":"...", "artists":["..."]}
  ]
}
```
## How it works
```bash
Kaggle dataset (tracks.csv, artists.csv, dict_artists.json)
       │
       ├─ scripts/prepare_parquet.py
       │    └─ catalog.parquet (tracks) + artist_genres.parquet (artist→genres)
       │
       └─ scripts/build_features.py
            ├─ derive: year (YYYY), pop_bucket (0..10)
            ├─ tokens: "genre tokens + year_Y + pop_P"
            ├─ vectorize: HashingVectorizer → 128-dim vectors
            └─ outputs: features.npz + meta.pkl
                                 │
                                 ▼
FastAPI (main.py)
  /search     -> scan titles in meta.pkl (substring + fuzzy)
  /recommend  -> cosine KNN + small bonus for same year/pop_bucket
```

### Why HashingVectorizer? 
Deterministic, zero training time, fast builds — ideal for an MVP.
### Reranking 
We add a tiny bonus (+0.02 each) if a candidate shares the **year** and/or **popularity** bucket with the query to improve relevance.

## Config (env vars you can override)
* `DATA_DIR` (default: `backend/app/data`)
* `FEATURES_PATH` (default: `$DATA_DIR/features.npz`)
* `META_PATH` (default: `$DATA_DIR/meta.pkl`)

Example:
```bash 
DATA_DIR=app/data META_PATH=app/data/meta.pkl FEATURES_PATH=app/data/features.npz \
python -m uvicorn app.main:app --reload
```

## Common pitfalls

* `FileNotFoundError: meta.pkl`
  Run `setup_data.sh` first, or use `run_api.sh` (paths pre-wired).
  Check: `ls backend/app/data/` for `features.npz` and `meta.pkl`.
* `ModuleNotFoundError: fastapi`
  Install deps: `python -m pip install -r backend/requirements.txt`.
* **Kaggle CLI “unauthorized”**
  Ensure `~/.kaggle/kaggle.json` exists and `chmod 600 ~/.kaggle/kaggle.json`.
* **Makefile errors**
We ship shell scripts instead; use setup_data.sh, run_api.sh, smoke_test.sh.

## Roadmap
* Stronger embeddings (text/audio) + **ANN index** (FAISS/ScaNN) for scale.
* Better search (BM25 or vector) + **artist diversity** in ranking.
* **Evaluation** (playlist continuation, offline metrics) + telemetry (latency, cache hits).
* Optional: Spotify OAuth for **playlist writes**.

## Dataset & license

Dataset: Kaggle `yamaerenay/spotify-dataset-19212020-600k-tracks`.
Review dataset terms/license before redistribution — raw data is **not** committed; scripts fetch locally.

## Dev notes
* Generated data lives in `backend/app/data/` and is gitignored (keep only `.gitkeep`).
* Scripts work from repo root **or** `backend/`; they resolve paths relative to themselves.