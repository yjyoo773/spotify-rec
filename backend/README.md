# Spotify Rec — Backend (MVP)

A lightweight, **file-backed** recommendation API you can run locally and demo in minutes.
**Pipeline**: Kaggle data → Parquet → 128-dim vectors → FastAPI routes. **No DB required**.

## What this does (at a glance)

1. Fetches the Kaggle dataset (tracks + artists).
2. Normalizes the needed CSVs into `app/data/`.
3. Builds **audio-feature** vectors (standardized + L2-normalized) into features.npz, with compact metadata in `meta.pkl`.
4. SServes a FastAPI with `/search` and `/recommend` (and `/file-recs/*`aliases) that returns vibe-similar tracks with era consistency.

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
      features.npz                  # vectors [N x D] (audio features only)
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

* Kaggle → Profile → Account → **Create New Token**

* Save to:
   * macOS/Linux: `~/.kaggle/kaggle.json` and `chmod 600 ~/.kaggle/kaggle.json`
   * Windows: `%USERPROFILE%\.kaggle\kaggle.json`

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
```
GET /file-recs/search?q=blinding%20lights&limit=10
GET /search?q=blinding%20lights&limit=10     # alias
```

### Response:
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
### Recommend (audio-feature cosine + era-aware re-rank)
``` bash
GET /file-recs/recommend?track_id=0VjIjW4GlUZAMYd2vXMi3b&k=20&bucket_bias=0.5
# alias:
GET /recommend?track_id=...&k=20&bucket_bias=0.5
```
* Accepts raw ID, `spotify:track:<id>`, or `https://open.spotify.com/track/<id>`
* Optional knobs:
  * `k` — number of results (default 25)

  * `bucket_bias` — shapes mainstream/indie mix (p ∝ count^bias). 1.0 = proportional; 0.0 = flatten; <0 favors rarer buckets.

### Response:
```json
{
  "query_id": "0VjIjW4GlUZAMYd2vXMi3b",
  "items": [
    {"id":"...", "score":0.83, "title":"...", "artists":["..."], "year": 2020, "pop_bucket": 8}
  ]
}
```
## How it works
```bash
Kaggle dataset (tracks.csv, artists.csv)
       │
       └─ scripts/setup_data.sh
            ├─ downloads & unzips into app/data/raw/
            ├─ normalizes → app/data/tracks.csv + app/data/artists.csv
            └─ runs build_features.py
                 ├─ parse year (YYYY), popularity bucket (pop//10)
                 ├─ standardize audio features (danceability, energy, valence, tempo, loudness, etc.)
                 ├─ L2-normalize rows → vibe vectors
                 └─ write features.npz + meta.pkl
                                 │
                                 ▼
FastAPI (main.py)
  /search     -> naive substring over titles in meta
  /recommend  -> cosine KNN (high recall)
                  → era prefilter (progressively widen window around seed median year)
                  → bucket-bias shortlist (p ∝ count^bias)
                  → small priors (year/pop proximity) + light artist de-dup

```

### Why audio features?
* Strong “vibe” without relying on genres or language (which may be sparse).
* Zero training step, fully offline, and reproducible.### Reranking 

### Reranking details
* **Era prior**: Gaussian bump around the seeds’ median year.
* **Popularity proximity**: small nudge for similar pop bucket.
* **Diversity**: light demotion for repeated primary artists.

## Config (env vars you can override)
* `DATA_DIR` (default: `backend/app/data`)
* `TRACKS_CSV`, `ARTISTS_CSV` (override input CSVs)
* `FEATURES_PATH` (default: `$DATA_DIR/features.npz`)
* `META_PATH` (default: `$DATA_DIR/meta.pkl`)

Example:
```bash 
DATA_DIR=app/data \
FEATURES_PATH=app/data/features.npz \
META_PATH=app/data/meta.pkl \
python -m uvicorn app.main:app --reload
```

## Common pitfalls

* `FileNotFoundError: meta.pkl`/ `features.npz`
  Run `setup_data.sh` first, or use `build_features.py` with proper env paths.
  Check: `ls backend/app/data/` for `features.npz` and `meta.pkl`.
* `ModuleNotFoundError: fastapi`
  Install deps: `python -m pip install -r backend/requirements.txt`.
* **Kaggle CLI “unauthorized”**
  Ensure `~/.kaggle/kaggle.json` exists and `chmod 600 ~/.kaggle/kaggle.json`.
* **Empty/strange recommendations**
  Check seeds exist in `features.npz;` ensure `tracks.csv` has audio columns and `build_features.py` ran successfully.

## Roadmap
* Stronger embeddings (text/audio) + **ANN index** (FAISS/ScaNN) for scale.
* Stronger diversification (MMR with pairwise audio-sim).
* Offline eval (playlist continuation, distance metrics) and telemetry.
* Optional: Spotify OAuth for **playlist writes**.

## Dataset & license

Dataset: Kaggle `yamaerenay/spotify-dataset-19212020-600k-tracks`.
Review dataset terms/license before redistribution — raw data is **not** committed; scripts fetch locally.

## Dev notes
* Generated data lives in `backend/app/data/` and is gitignored (keep only `.gitkeep`).
* Scripts work from repo root **or** `backend/`; they resolve paths relative to themselves.