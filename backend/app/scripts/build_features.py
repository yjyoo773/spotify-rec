from __future__ import annotations
import os, json, re, pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

# -------- Paths (override via env if needed) --------
ROOT_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR   = os.environ.get("DATA_DIR", os.path.join(ROOT_DIR, "data"))
TRACKS_CSV = os.environ.get("TRACKS_CSV", os.path.join(DATA_DIR, "tracks.csv"))
ARTISTS_CSV= os.environ.get("ARTISTS_CSV", os.path.join(DATA_DIR, "artists.csv"))
FEATURES_OUT = os.environ.get("FEATURES_PATH", os.path.join(DATA_DIR, "features.npz"))
META_OUT     = os.environ.get("META_PATH",     os.path.join(DATA_DIR, "meta.pkl"))

AUDIO_COLS = [
    "danceability","energy","speechiness","acousticness","instrumentalness",
    "liveness","valence","tempo","loudness"
]

def _parse_year(x):
    try:
        y = int(str(x).split("-")[0])
        return y if 1900 <= y <= 2030 else None
    except Exception:
        return None

def _coerce_artists(cell):
    # Use tracks.csv "artists" if present; fallback to [].
    if isinstance(cell, list):
        return [str(a) for a in cell]
    if isinstance(cell, str):
        s = cell.strip()
        if s.startswith("["):
            # JSON-ish list
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(a) for a in arr]
            except Exception:
                pass
        # comma/semicolon separated fallback
        return [t.strip() for t in re.split(r",|;", s) if t.strip()]
    return []

def main():
    if not os.path.exists(TRACKS_CSV):
        raise FileNotFoundError(f"tracks.csv not found at {TRACKS_CSV}")

    tr = pd.read_csv(TRACKS_CSV)
    # Optional: artists CSV only for future enrichment; we don't require it here.
    if os.path.exists(ARTISTS_CSV):
        ar = pd.read_csv(ARTISTS_CSV)[["id","name"]].rename(columns={"id":"artist_id","name":"artist_name"})
    else:
        ar = pd.DataFrame(columns=["artist_id","artist_name"])

    # ---------- Meta ----------
    ids = tr["id"].astype(str).tolist()
    years = tr["release_date"].apply(_parse_year).tolist()
    pop_bucket = (tr["popularity"].fillna(0).astype(int) // 10).tolist()
    artist_names = tr["artists"].apply(_coerce_artists).tolist()

    meta = {}
    for tid, title, names, yr, pb in zip(ids, tr["name"].astype(str), artist_names, years, pop_bucket):
        meta[str(tid)] = {
            "title": title,
            "artist_names": names,
            "year": yr,
            "pop_bucket": int(pb) if pb is not None else None,
            "genres": [],  # intentionally empty; we don't rely on genres
        }

    # ---------- Features (audio only) ----------
    # Ensure all audio columns exist; create safe defaults if missing.
    for c in AUDIO_COLS:
        if c not in tr.columns:
            tr[c] = 0.0

    X = tr[AUDIO_COLS].astype(float).copy()
    # Clip a few outliers to keep scale sane
    if "loudness" in X.columns:
        X["loudness"] = X["loudness"].clip(-60, 0)
    if "tempo" in X.columns:
        X["tempo"] = X["tempo"].clip(40, 220)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    # L2 normalize per track
    vecs = Xs.astype("float32")
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    vecs = (vecs / norms).astype("float32")

    # ---------- Persist ----------
    os.makedirs(os.path.dirname(FEATURES_OUT), exist_ok=True)
    np.savez_compressed(FEATURES_OUT, ids=np.array(ids, dtype=object), vecs=vecs)

    os.makedirs(os.path.dirname(META_OUT), exist_ok=True)
    with open(META_OUT, "wb") as f:
        pickle.dump(meta, f)

    print(f"Wrote {FEATURES_OUT} (ids={len(ids)}, dim={vecs.shape[1]})")
    print(f"Wrote {META_OUT}    (meta entries={len(meta)})")

if __name__ == "__main__":
    main()