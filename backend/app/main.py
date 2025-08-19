from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from .settings import settings
from .spotify_client import get_playlist, get_playlist_tracks, get_tracks_batch, add_tracks_to_playlist
from .recommender.data_prep import data_prep
from .recommender.feature_engineering import create_feature_set
from .recommender.playlist_vector import playlist_vector
from .recommender.recommend import recommend_tracks
from .recommender.on_the_fly import build_on_the_fly_features
from .cache import get_cache, set_cache, make_playlist_snapshot_key
from .db import SessionLocal
from .models import TrackFeature
from pydantic import BaseModel
import time

app = FastAPI(title="Spotify Playlist Recommender")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

catalog_df = pd.DataFrame()
features_df = pd.DataFrame()
genre_df = pd.DataFrame()

@app.on_event("startup")
def startup():
    global catalog_df, features_df, genre_df
    try:
        catalog_df = pd.read_csv(settings.CATALOG_PATH)
    except Exception as e:
        print("No catalog loaded:", e)
        catalog_df = pd.DataFrame()
    try:
        genre_df = pd.read_csv(settings.GENRE_PATH)
    except Exception as e:
        print("No genre file loaded:", e)
        genre_df = pd.DataFrame()
    if not catalog_df.empty and not genre_df.empty:
        catalog_df = data_prep(catalog_df, genre_df, settings.POP_SPLIT)
        features_df = create_feature_set(catalog_df)
        print("Loaded catalog, tracks:", len(catalog_df))
    else:
        print("Catalog/genre not loaded — on-the-fly mode only")

class RecommendRequest(BaseModel):
    playlist_id: str
    access_token: str
    top_k: int = 20
    weight_factor: float = 1.15

class AddTrackRequest(BaseModel):
    access_token: str
    track_uri: str

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/recommend")
def recommend(req: RecommendRequest):
    pl_meta = get_playlist(req.access_token, req.playlist_id)
    owner_id = pl_meta.get("owner", {}).get("id", "unknown")
    snapshot = pl_meta.get("snapshot_id", str(time.time()))
    cache_key = make_playlist_snapshot_key(owner_id, req.playlist_id, snapshot)
    cached = get_cache(cache_key)
    if cached:
        return cached

    playlist_tracks = get_playlist_tracks(req.access_token, req.playlist_id)
    if not playlist_tracks:
        raise HTTPException(status_code=404, detail="playlist empty or not found")
    pl_df = pd.DataFrame(playlist_tracks).dropna(subset=["id"])
    pl_df["added_at"] = pd.to_datetime(pl_df["added_at"])

    missing_ids = []
    have_ids = set()
    with SessionLocal() as session:
        if not pl_df.empty:
            q = session.query(TrackFeature).filter(TrackFeature.id.in_(pl_df["id"].tolist()))
            for row in q:
                have_ids.add(row.id)
    missing_ids = [tid for tid in pl_df["id"].tolist() if tid not in have_ids]

    if missing_ids:
        artist_map = {t['id']: t.get('artist_ids', []) for t in playlist_tracks}
        onfly_feats = build_on_the_fly_features(req.access_token, missing_ids, artist_map)
        # Optionally upsert vecs with pgvector_utils here

        # reload features_df if we have catalog in memory
        if 'features_df' in globals() and not features_df.empty:
            # naive append — in prod, re-generate or store in DB and query
            features_df = pd.concat([features_df, onfly_feats], ignore_index=True)

    if 'features_df' not in globals() or features_df.empty:
        raise HTTPException(status_code=400, detail="No features available to compute recommendations (seed catalog or use on-the-fly endpoint).")

    pl_subset = pl_df[["id","added_at"]].rename(columns={"added_at":"date_added"})
    pl_vec, nonplaylist_feats = playlist_vector(features_df, pl_subset, req.weight_factor)
    if pl_vec is None:
        raise HTTPException(status_code=400, detail="Could not construct playlist vector.")

    recs = recommend_tracks(catalog_df, pl_vec, nonplaylist_feats, top_k=req.top_k)
    rec_ids = recs["id"].tolist()
    meta = get_tracks_batch(req.access_token, rec_ids) if rec_ids else []
    meta_map = {m["id"]: m for m in meta if m and m.get("id")}
    out = []
    for _, r in recs.iterrows():
        m = meta_map.get(r["id"], {})
        images = (m.get("album", {}).get("images") or []) if m else []
        img = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else "")
        artists = ", ".join([a["name"] for a in m.get("artists", [])]) if m else ""
        out.append({
            "id": r["id"],
            "name": m.get("name") or r.get("id"),
            "artists": artists,
            "album_image": img,
            "similarity": float(r["sim"])
        })

    set_cache(cache_key, out, ttl=60*10)
    return out

@app.post("/playlists/{playlist_id}/add")
def add_to_playlist(playlist_id: str, body: AddTrackRequest):
    resp = add_tracks_to_playlist(body.access_token, playlist_id, [body.track_uri])
    return {"ok": True, "spotify_response": resp}