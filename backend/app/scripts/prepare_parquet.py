import os, json, pandas as pd, numpy as np, ast
from pathlib import Path

RAW = Path(os.environ.get("RAW_DIR", "backend/app/data/raw"))
OUT = Path(os.environ.get("DATA_DIR", "backend/app/data"))
OUT.mkdir(parents=True, exist_ok=True)

ARTISTS_CSV = RAW / "artists.csv"
TRACKS_CSV  = RAW / "tracks.csv"
DICT_JSON   = RAW / "dict_artists.json"  # optional

def parse_listish(x):
    """Parse list-ish fields that might be a list, JSON string, Python repr, or empty."""
    if isinstance(x, list):
        return x
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return []
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return []
    # Try JSON first
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else []
    except Exception:
        pass
    # Then Python literal (handles single quotes)
    try:
        v = ast.literal_eval(s)
        return v if isinstance(v, list) else []
    except Exception:
        # Last-resort splitter
        s = s.strip("[]")
        parts = [p.strip().strip("'\"") for p in s.split(",") if p.strip()]
        return parts

def normalize_genres(g):
    v = parse_listish(g)
    # Dedup while preserving order; keep it short to avoid huge tokens later
    seen = set()
    out = []
    for item in v:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
        if len(out) >= 25:
            break
    return out

def make_catalog_and_artist_genres():
    tracks = pd.read_csv(TRACKS_CSV, low_memory=False)
    t = tracks[["id","name","id_artists","release_date","popularity"]].rename(columns={"name":"title"}).copy()

    # Robust artist_ids parsing
    t["artist_ids"] = t["id_artists"].apply(parse_listish)
    t.drop(columns=["id_artists"], inplace=True)

    # Ensure expected dtypes
    t["id"] = t["id"].astype(str)
    t["title"] = t["title"].astype(str)
    t["release_date"] = t["release_date"].astype(str)
    t["popularity"] = pd.to_numeric(t["popularity"], errors="coerce").fillna(0).astype(int)

    # Write catalog.parquet
    t.to_parquet(OUT / "catalog.parquet", index=False)

    artists = pd.read_csv(ARTISTS_CSV, low_memory=False)
    a = artists[["id","genres","name","popularity"]].copy()
    a["id"] = a["id"].astype(str)
    a["name"] = a["name"].astype(str)
    a["popularity"] = pd.to_numeric(a["popularity"], errors="coerce").fillna(0).astype(int)
    a["genres"] = a["genres"].apply(normalize_genres)

    a.to_parquet(OUT / "artist_genres.parquet", index=False)

def make_artist_knn(top_k=10):
    if not DICT_JSON.exists():
        return
    # dict_artists.json structure can vary; handle common shapes
    rows = []
    with open(DICT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect: { "artist_id": ["rec_id1", "rec_id2", ...] }  OR
    # { "artist_id": [{"id": "rec_id", "weight": ...}, ...] }
    for aid, recs in data.items():
        if isinstance(recs, list):
            for r in recs[:top_k]:
                if isinstance(r, str):
                    rows.append((aid, r, 1.0))
                elif isinstance(r, dict):
                    rid = r.get("id") or r.get("artist_id") or r.get("id_rec")
                    if rid:
                        rows.append((aid, rid, float(r.get("weight", 1.0))))
    if rows:
        pd.DataFrame(rows, columns=["artist_id","rec_artist_id","weight"]).to_parquet(
            OUT / "artist_knn.parquet", index=False
        )

if __name__ == "__main__":
    make_catalog_and_artist_genres()
    make_artist_knn(top_k=10)
    print("Wrote catalog.parquet, artist_genres.parquet, artist_knn.parquet (optional).")
