# Spotify Recommender Backend (monorepo)

## What is included
- FastAPI backend with:
  - Raw Spotify Web API usage (no spotipy)
  - On-the-fly feature extraction (audio-features + artist->genres)
  - Redis caching for playlist snapshots
  - Exponential backoff + rate-limit handling
  - Postgres persistence + pgvector hooks
  - RQ-based background tasks for refreshing catalog
  - Pytest + pytest-asyncio test suite for key endpoints and Spotify client functions

## Quickstart (docker)
1. Copy `.env.example` -> `.env` and fill `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`.
2. Put `catalog.csv` and `artist_genres.csv` in `backend/app/data/` (optional; on-the-fly works but catalog speeds things).
3. Make sure Docker Desktop (or Colima) is running on your machine.
4. Build and run:
   ```bash
   docker compose up --build
   ```
5. The API will be available at http://localhost:8000.

6. Test the backend with:
   ```
   docker exec -it backend_app_container_name pytest
   ```
or, if running locally in your venv:
   ```
   pytest
   ```
## Notes
- Endpoint for health check: `/healthz`
- Recommendations endpoint: `/recommend` (POST)
- Add track endpoint: `/playlists/{playlist_id}/add` (POST)
- Cached playlist snapshots stored in Redis for 10 minutes
- Catalog refresh handled via RQ background jobs

## Development Notes
- `backend/app/main.py` → FastAPI entrypoint, endpoints, startup catalog load
- `backend/app/settings.py` → App configuration (BaseSettings)
- `backend/app/spotify_client.py` → Spotify Web API client with backoff and rate-limit handling
- `backend/app/recommender/` → Recommendation logic:
- `data_prep.py` → preprocess catalog & genre data
- `feature_engineering.py` → generate features for tracks
- `playlist_vector.py` → create playlist embedding
- `recommend.py` → compute top-K recommendations
- `on_the_fly.py` → build features for tracks not in catalog
- `backend/app/cache.py` → Redis caching helpers
- `backend/app/db.py` → database session & connection
- `backend/app/models.py` → ORM models for tracks & features
- Tests live in `backend/tests/` and use pytest + pytest-asyncio
