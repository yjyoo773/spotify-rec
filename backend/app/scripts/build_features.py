import os, json, ast, pickle, numpy as np, pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import HashingVectorizer
from typing import Dict, List

DATA = Path(os.environ.get("DATA_DIR", "backend/app/data"))
CAT_PATH = DATA / "catalog.parquet"
ART_PATH = DATA / "artist_genres.parquet"

VECTOR_DIM = int(os.environ.get("VECTOR_DIM", "128"))
POP_SPLIT = int(os.environ.get("POP_SPLIT", "10"))

def _to_list_ids(x) -> List[str]:
    """Make artist_ids a plain Python list[str] regardless of how Parquet stored it."""
    if isinstance(x, list):
        return [str(i) for i in x]
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return []
    if isinstance(x, tuple):
        return [str(i) for i in x]
    if isinstance(x, np.ndarray):
        return [str(i) for i in x.tolist()]
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return []
        for parser in (json.loads, ast.literal_eval):
            try:
                v = parser(s)
                if isinstance(v, (list, tuple, np.ndarray)):
                    return [str(i) for i in list(v)]
            except Exception:
                pass
        s = s.strip("[]")
        parts = [p.strip().strip("'\"") for p in s.split(",") if p.strip()]
        return parts
    try:
        return [str(i) for i in list(x)]
    except Exception:
        return []

def _safe_year(series: pd.Series) -> pd.Series:
    """Derive 4-digit year from release_date robustly."""
    # Try pandas datetime first
    dt = pd.to_datetime(series, errors="coerce", utc=True)
    year = dt.dt.year.astype("Int64")  # nullable int
    # Fill any nulls by string slicing fallback
    missing = year.isna()
    if missing.any():
        s = series.astype(str).str.extract(r"^(\d{4})", expand=False)
        year = year.mask(missing, s)
    # Final cleanup: string, default '0000' if still missing
    year = year.astype(str).replace({"<NA>": "0000", "nan": "0000"})
    return year

def load_frames():
    if not CAT_PATH.exists():
        raise FileNotFoundError(f"Missing {CAT_PATH}. Run prepare_parquet.py first.")
    if not ART_PATH.exists():
        raise FileNotFoundError(f"Missing {ART_PATH}. Run prepare_parquet.py first.")

    cat = pd.read_parquet(CAT_PATH)
    art = pd.read_parquet(ART_PATH)

    # id -> genres, id -> name
    aid2genres: Dict[str, List[str]] = dict(
        zip(art["id"].astype(str), art["genres"].apply(lambda v: v if isinstance(v, list) else []))
    )
    aid2name: Dict[str, str] = dict(zip(art["id"].astype(str), art["name"].astype(str)))

    # normalize artist_ids
    cat["artist_ids"] = cat["artist_ids"].apply(_to_list_ids)

    # derive genres per track
    def track_genres(aids: List[str]) -> List[str]:
        out: List[str] = []
        for aid in _to_list_ids(aids):
            out.extend(aid2genres.get(aid, []))
        # dedup preserve order, cap
        seen = set()
        ded = []
        for g in out:
            if g and g not in seen:
                seen.add(g); ded.append(g)
            if len(ded) >= 25:
                break
        return ded

    # derive artist names per track
    def track_names(aids: List[str]) -> List[str]:
        return [aid2name.get(a, a) for a in _to_list_ids(aids)]

    cat["genres"] = cat["artist_ids"].apply(track_genres)
    cat["artist_names"] = cat["artist_ids"].apply(track_names)

    # ensure core fields exist
    if "release_date" not in cat.columns:
        # shouldn't happen if prepare_parquet.py ran, but be defensive
        cat["release_date"] = ""

    # year + pop bucket
    cat["year"] = _safe_year(cat["release_date"])
    cat["popularity"] = pd.to_numeric(cat.get("popularity", 0), errors="coerce").fillna(0).astype(int)
    cat["pop_bucket"] = (cat["popularity"] // POP_SPLIT).clip(lower=0, upper=10).astype(int)

    return cat

def build():
    cat = load_frames()

    # tokens: genres + year + popularity bucket
    cat["tokens"] = (
        cat["genres"].apply(lambda xs: " ".join(xs)) +
        " year_" + cat["year"].astype(str) +
        " pop_" + cat["pop_bucket"].astype(str)
    )

    vec = HashingVectorizer(n_features=VECTOR_DIM, norm=None, alternate_sign=False)
    X = vec.transform(cat["tokens"].fillna("").tolist()).astype(np.float32).toarray()

    ids = cat["id"].astype(str).to_numpy()

    # Build meta with names
    meta = {
        tid: {
            "title": row["title"],
            "artists": row["artist_ids"],                # keep IDs if you need them internally
            "artist_names": row["artist_names"],         # names for API/search
            "year": str(row["year"]),
            "pop_bucket": int(row["pop_bucket"]),
        }
        for tid, row in cat.set_index("id").iterrows()
    }

    DATA.mkdir(parents=True, exist_ok=True)
    np.savez(DATA / "features.npz", ids=ids, vectors=X)
    with open(DATA / "meta.pkl", "wb") as f:
        pickle.dump(meta, f)

    print("Built features.npz and meta.pkl (with artist_names)")

if __name__ == "__main__":
    build()