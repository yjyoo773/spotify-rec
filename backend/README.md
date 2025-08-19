# Spotify Recommender Backend (monorepo)

## What is included
- FastAPI backend with:
  - Raw Spotify Web API usage (no spotipy)
  - On-the-fly feature extraction (audio-features + artist->genres)
  - Redis caching for playlist snapshots
  - Exponential backoff + rate-limit handling
  - Postgres persistence + pgvector hooks
  - RQ-based background tasks for refreshing catalog

## Quickstart (docker)
1. copy `.env.example` -> `.env` and fill `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`.
2. Put `catalog.csv` and `artist_genres.csv` in `backend/app/data/` (optional; on-the-fly works but catalog speeds things).
3. Build and run:
   ```bash
   docker-compose up --build