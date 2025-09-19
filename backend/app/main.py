from __future__ import annotations

import os
import pickle
import difflib
from typing import Dict, List, Tuple

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ---- File-backed recommender (features.npz + meta.pkl) ----
# This is the only new dependency within your codebase.
# It lazy-loads vectors/meta on first request.
from .recommender.file_backend import recommend_from_file

# ---------- FastAPI app ----------
app = FastAPI(
    title="spotify-rec",
    version=os.environ.get("APP_VERSION", "mvp-0.1"),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (dev-friendly; tighten for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # set to your frontend origin(s) in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Simple META loader for search ----------
THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(THIS_DIR, "data"))
META_PATH = os.environ.get("META_PATH", os.path.join(DATA_DIR, "meta.pkl"))

_META: Dict[str, dict] | None = None
_TITLE_INDEX: List[Tuple[str, str]] | None = None  # (lower_title, track_id)


def _ensure_meta_loaded() -> None:
    """Lazily load meta.pkl and build a lowercase title index for naive search."""
    global _META, _TITLE_INDEX
    if _META is not None and _TITLE_INDEX is not None:
        return
    with open(META_PATH, "rb") as f:
        _META = pickle.load(f)  # {track_id: {"title": ..., "artists": [...], "year":..., "pop_bucket":...}}
    # Build a small searchable index (title_lower -> id)
    _TITLE_INDEX = []
    for tid, m in _META.items():
        title = (m.get("title") or "").strip()
        if title:
            _TITLE_INDEX.append((title.lower(), tid))


def _search_titles(q: str, limit: int = 10) -> List[dict]:
    """Very light search over titles (substring + fuzzy fallback)."""
    _ensure_meta_loaded()
    assert _META is not None and _TITLE_INDEX is not None

    ql = q.strip().lower()
    if not ql:
        return []

    # 1) Simple substring filter
    hits = [(t, tid) for (t, tid) in _TITLE_INDEX if ql in t]
    # 2) If too few, add fuzzy matches
    if len(hits) < limit:
        universe = [t for (t, _tid) in _TITLE_INDEX]
        fuzzy = difflib.get_close_matches(ql, universe, n=limit * 3, cutoff=0.6)
        fuzzy_set = set(fuzzy)
        hits.extend([(t, tid) for (t, tid) in _TITLE_INDEX if t in fuzzy_set])

    # Dedup while preserving order, then map to payload
    out: List[dict] = []
    seen = set()
    for _, tid in hits:
        if tid in seen:
            continue
        seen.add(tid)
        m = _META[tid]
        out.append(
            {
                "id": tid,
                "title": m.get("title"),
                "artists": m.get("artists"),
                "year": m.get("year"),
                "pop_bucket": m.get("pop_bucket"),
            }
        )
        if len(out) >= limit:
            break
    return out


# ---------- Health ----------
@app.get("/health")
def health():
    return {"status": "ok", "service": "spotify-rec", "mode": "file-backed"}


@app.get("/file-recs/health")
def file_recs_health():
    # Probe that meta is readable; vectors load lazily via recommend_from_file.
    try:
        _ensure_meta_loaded()
        ready = True
    except Exception:
        ready = False
    return {"status": "ok", "ready": ready}


# ---------- Search & Recommend (file-backed) ----------
@app.get("/file-recs/search")
def file_recs_search(q: str, limit: int = Query(10, ge=1, le=50)):
    results = _search_titles(q, limit=limit)
    return {"query": q, "items": results}


@app.get("/file-recs/recommend")
def file_recs_recommend(
    track_id: str,
    k: int = Query(25, ge=1, le=100),
    bucket_bias: float = 1.0,
):
    items = recommend_from_file(track_id=track_id, k=k, bucket_bias=bucket_bias)
    if not items:
        # Either the id isn't in features/meta OR it has no neighbors in the top-K window.
        # Offer a helpful hint by returning a few search results that *look like* the id.
        suggestions = []
        try:
            suggestions = _search_titles(track_id, limit=5)
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail={"message": f"unknown or cold track_id: {track_id}", "suggestions": suggestions},
        )
    return {"query_id": track_id, "items": items}


# ---------- Compatibility aliases (optional, handy for existing frontends) ----------
@app.get("/search")
def search_alias(q: str, limit: int = Query(10, ge=1, le=50)):
    return file_recs_search(q=q, limit=limit)  # re-use implementation


@app.get("/recommend")
def recommend_alias(
    track_id: str,
    k: int = Query(25, ge=1, le=100),
    bucket_bias: float = 1.0,
):
    return file_recs_recommend(track_id=track_id, k=k, bucket_bias=bucket_bias)