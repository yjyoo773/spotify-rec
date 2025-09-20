from __future__ import annotations

import os
import pickle
import difflib
import re
import unicodedata
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
_WORD = re.compile(r"\w+", flags=re.UNICODE)

def _norm(s: str) -> str:
    """lowercase + strip accents/diacritics + collapse spaces"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = " ".join(s.split())
    return s

def _ensure_meta_loaded() -> None:
    global _META, _INDEX
    if _META is not None and _INDEX is not None:
        return
    with open(META_PATH, "rb") as f:
        _META = pickle.load(f)  # {track_id: {"title":..., "artists":[...], "year":..., "pop_bucket":...}}
    _INDEX = []
    for tid, m in _META.items():
        title = _norm(m.get("title") or "")
        if not title:
            continue
        artists = [ _norm(aid) for aid in (m.get("artists") or []) ]  # note: these are artist IDs in your meta
        # If you have artist NAMES available, swap to names here. Otherwise we only index titles.
        pop = int(m.get("pop_bucket") or 0)
        _INDEX.append((title, tid, artists, pop))
        
def _score_match(q: str, title: str, artists: List[str], pop_bucket: int) -> float:
    """
    Heuristic scoring:
      +100 exact title
      +85 exact phrase (word-boundaries)
      +70 startswith phrase
      + up to +40 for token coverage of title
      +10 if any artist token appears in query (if names indexed)
      + small boost for popularity bucket
    Fallback: fuzzy ratio (difflib) * 0.4
    """
    score = 0.0

    # exact title
    if q == title:
        score += 100.0
    # phrase (word boundaries)
    elif re.search(rf"\b{re.escape(q)}\b", title):
        score += 85.0
    # starts with
    elif title.startswith(q):
        score += 70.0

    # token coverage on title
    q_toks = _WORD.findall(q)
    t_toks = set(_WORD.findall(title))
    if q_toks:
        covered = sum(1 for t in q_toks if t in t_toks)
        score += 40.0 * (covered / len(q_toks))

    # artist boost — only works if you index artist names (see note above)
    # keeping small so it doesn't dominate
    if artists:
        a_cover = sum(1 for a in artists if a and a in q)
        if a_cover > 0:
            score += 10.0

    # popularity tie-break (tiny)
    score += min(max(pop_bucket, 0), 10) * 0.5

    # fuzzy fallback if still low
    if score < 60.0:
        fuzz = difflib.SequenceMatcher(None, q, title).ratio()
        score = max(score, 40.0 + 40.0 * fuzz)  # 40..80 depending on fuzz

    return score


def _search_titles(q: str, limit: int = 10) -> List[dict]:
    _ensure_meta_loaded()
    assert _META is not None and _INDEX is not None

    qn = _norm(q)
    if not qn:
        return []

    # rank all, then take top N (N small so this is fine)
    scored = []
    for title, tid, artists, pop in _INDEX:
        s = _score_match(qn, title, artists, pop)
        if s > 0:
            scored.append((s, tid))

    # sort by score desc, then by pop desc (as secondary), then by title asc for stability
    # fetch pop and title on-demand from _META for tie-breaks
    def key(pair):
        s, tid = pair
        m = _META.get(tid, {})
        return (-s, -(m.get("pop_bucket") or 0), m.get("title") or "")

    scored.sort(key=key)

    out: List[dict] = []
    seen_titles = set()
    for _, tid in scored:
        m = _META[tid]
        title_disp = m.get("title") or ""
        title_key = _norm(re.sub(r"\(.*?\)|\[.*?\]", "", title_disp))  # strip bracketed variants for dedupe
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        out.append({
            "id": tid,
            "title": title_disp,
            "artists": m.get("artist_names") or m.get("artists"),  # prefer names
            "year": m.get("year"),
            "pop_bucket": m.get("pop_bucket"),
        })
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