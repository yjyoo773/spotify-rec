import os, json, ast, pickle, numpy as np, pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import HashingVectorizer

DATA = Path(os.environ.get("DATA_DIR", "backend/app/data"))
VECTOR_DIM = int(os.environ.get("VECTOR_DIM", "128"))
POP_SPLIT = int(os.environ.get("POP_SPLIT", "10"))

def _to_list_ids(x):
    """Make artist_ids a plain Python list regardless of how Parquet/Arrow stored it."""
    if isinstance(x, list):
        return x
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return []
    if isinstance(x, (np.ndarray, tuple)):
        return [str(i) for i in x.tolist()]
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return []
        # try JSON then Python literal (handles single quotes)
        for parser in (json.loads, ast.literal_eval):
            try:
                v = parser(s)
                return list(v) if isinstance(v, (list, tuple, np.ndarray)) else []
            except Exception:
                pass
        # last ditch: split brackets/comma
        s = s.strip("[]")
        return [p.strip().strip("'\"") for p in s.split(",") if p.strip()]
    # unknown type
    try:
        return list(x)
    except Exception:
        return []

def load_data():
    cat = pd.read_parquet(DATA / "catalog.parquet")
    arts = pd.read_parquet(DATA / "artist_genres.parquet")

    # ensure artist_ids is list-of-str
    cat["artist_ids"] = cat["artist_ids"].apply(_to_list_ids).apply(lambda xs: [str(i) for i in xs])

    # build artist_id -> genres list
    aid2genres = {str(k): (v if isinstance(v, list) else []) for k, v in zip(arts["id"].astype(str), arts["genres"])}

    def track_genres(aids):
        out = []
        for aid in _to_list_ids(aids):
            out.extend(aid2genres.get(str(aid), []))
        # dedup while preserving order; cap length to avoid huge tokens
        seen = set()
        uniq = []
        for g in out:
            if g and g not in seen:
                seen.add(g)
                uniq.append(g)
            if len(uniq) >= 25:
                break
        return uniq

    cat["genres"] = cat["artist_ids"].apply(track_genres)
    return cat

def build():
    cat = load_data()

    # year & pop bucket
    cat["year"] = cat["release_date"].astype(str).str[:4]
    cat["pop_bucket"] = pd.to_numeric(cat["popularity"], errors="coerce").fillna(0).astype(int) // POP_SPLIT

    # tokens = genres + year + pop
    cat["tokens"] = (
        cat["genres"].apply(lambda xs: " ".join(xs)) + 
        " year_" + cat["year"].astype(str) + 
        " pop_" + cat["pop_bucket"].astype(str)
    )

    vec = HashingVectorizer(n_features=VECTOR_DIM, norm=None, alternate_sign=False)
    X = vec.transform(cat["tokens"].fillna("").tolist()).astype(np.float32).toarray()

    ids = cat["id"].astype(str).to_numpy()
    meta = {
        tid: {
            "title": row.title,
            "artists": row.artist_ids,   # already normalized to list
            "year": str(row.year),
            "pop_bucket": int(row.pop_bucket),
        }
        for tid, row in cat.set_index("id").iterrows()
    }

    np.savez(DATA / "features.npz", ids=ids, vectors=X)
    with open(DATA / "meta.pkl", "wb") as f:
        pickle.dump(meta, f)
    print("Built features.npz and meta.pkl")

if __name__ == "__main__":
    build()