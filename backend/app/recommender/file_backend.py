from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import os, pickle
from urllib.parse import urlparse
import numpy as np
from collections import Counter

# Paths (resolve relative to package)
THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(THIS_DIR), "data"))
FEATURES_PATH = os.environ.get("FEATURES_PATH", os.path.join(DATA_DIR, "features.npz"))
META_PATH = os.environ.get("META_PATH", os.path.join(DATA_DIR, "meta.pkl"))

def _norm_id(x: str) -> str:
    s = (x or "").strip()
    if not s: return s
    if s.startswith("spotify:"): return s.rsplit(":", 1)[-1]
    if "open.spotify.com" in s:
        parts = [p for p in urlparse(s).path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "track": return parts[1]
    return s

@dataclass
class FileStore:
    ids: np.ndarray
    vecs: np.ndarray
    id2idx: Dict[str, int]
    meta: Dict[str, dict]

    @classmethod
    def load(cls) -> "FileStore":
        dat = np.load(FEATURES_PATH, allow_pickle=True)
        ids = dat["ids"]
        vecs = dat["vectors"].astype(np.float32)
        with open(META_PATH, "rb") as f:
            meta = pickle.load(f)
        id2idx = {str(t): i for i, t in enumerate(ids)}
        return cls(ids=ids, vecs=vecs, id2idx=id2idx, meta=meta)

    def vector(self, track_id: str) -> Optional[np.ndarray]:
        i = self.id2idx.get(str(track_id))
        return None if i is None else self.vecs[i]

def _cosine_knn(q: np.ndarray, M: np.ndarray, ids: np.ndarray, top_k: int = 50) -> List[Tuple[str, float]]:
    qn = q / (np.linalg.norm(q) + 1e-8)
    Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-8)
    sims = Mn @ qn
    k = min(top_k, len(sims))
    idxs = np.argpartition(-sims, range(k))[:k]
    idxs = idxs[np.argsort(-sims[idxs])]
    return [(str(ids[i]), float(sims[i])) for i in idxs]

def _jaccard(a: List[str] | None, b: List[str] | None) -> float:
    A, B = set(a or []), set(b or [])
    if not A or not B: return 0.0
    inter = len(A & B); uni = len(A | B)
    return inter / uni if uni else 0.0

def _primary_artist(m: dict) -> Optional[str]:
    arr = m.get("artist_names") or m.get("artists") or []
    return arr[0] if arr else None

def _make_profile(metas: List[dict]) -> dict:
    """Aggregate profile from one or more seed tracks: median year, mean pop_bucket, top genres."""
    years = []
    pops = []
    g_counter = Counter()
    seed_artists: Set[str] = set()
    for m in metas:
        y = m.get("year")
        if isinstance(y, str) and y.isdigit():
            years.append(int(y))
        elif isinstance(y, int):
            years.append(y)
        p = m.get("pop_bucket")
        if isinstance(p, (int, np.integer)) or (isinstance(p, str) and p.isdigit()):
            pops.append(int(p))
        for g in (m.get("genres") or []):
            if g:
                g_counter[g] += 1
        pa = _primary_artist(m)
        if pa:
            seed_artists.add(pa)

    year_med = None
    if years:
        years.sort()
        year_med = years[len(years)//2]

    pop_mean = None
    if pops:
        pop_mean = int(round(sum(pops) / len(pops)))

    top_genres = [g for g, _ in g_counter.most_common(20)]

    return {
        "year": year_med,            # int or None
        "pop_bucket": pop_mean,      # int or None
        "genres": top_genres,        # list[str]
        "seed_artists": seed_artists # set[str]
    }

def _same_decade(y1: Optional[int], y2: Optional[int]) -> bool:
    if y1 is None or y2 is None:
        return False
    return (y1 // 10) == (y2 // 10)

def _pop_close(p1: Optional[int], p2: Optional[int]) -> float:
    """Return small closeness bonus 0..1 based on absolute gap (0 best)."""
    if p1 is None or p2 is None:
        return 0.0
    gap = abs(int(p1) - int(p2))
    return max(0.0, 1.0 - min(gap, 10) / 10.0)  # linear drop-off

def _rerank_with_profile(
    cands: List[Tuple[str, float]], store: FileStore, profile: dict, boost: float = 1.0
):
    q_year = profile.get("year")
    q_pop = profile.get("pop_bucket")
    q_genres = profile.get("genres") or []
    seed_artists: Set[str] = profile.get("seed_artists") or set()

    def bonus(tid: str) -> float:
        m = store.meta.get(str(tid), {})
        b = 0.0
        # decade nudge
        y = m.get("year")
        y_int = int(y) if isinstance(y, (int, np.integer)) or (isinstance(y, str) and y.isdigit()) else None
        if _same_decade(q_year, y_int): 
            b += 0.02
        # popularity closeness (tiny)
        b += 0.02 * _pop_close(q_pop, m.get("pop_bucket"))
        # genre overlap
        b += 0.10 * _jaccard(q_genres, m.get("genres") or [])
        # diversity: slight penalty if candidate artist is one of seed artists
        if _primary_artist(m) in seed_artists:
            b -= 0.03
        return b * boost

    return sorted(cands, key=lambda p: p[1] + bonus(p[0]), reverse=True)

# -------- Single-seed entry --------
def recommend_from_file(
    track_id: str, k: int = 25, bucket_bias: float = 1.0,
    require_genre: str | None = None
) -> List[dict]:
    track_id = _norm_id(track_id)

    store = recommend_from_file._store  # type: ignore[attr-defined]
    if store is None:
        store = FileStore.load()
        recommend_from_file._store = store  # type: ignore[attr-defined]

    v = store.vector(track_id)
    if v is None:
        return []

    raw = _cosine_knn(v, store.vecs, store.ids, top_k=max(k * 6, 60))
    raw = [(tid, s) for (tid, s) in raw if tid != str(track_id)]

    # build profile from the single seed
    qmeta = store.meta.get(str(track_id), {})
    profile = _make_profile([qmeta])

    ranked = _rerank_with_profile(raw, store, profile, boost=bucket_bias)

    if require_genre:
        rg = require_genre.lower().strip()
        ranked = [(tid, s) for (tid, s) in ranked if rg in (store.meta.get(tid, {}).get("genres") or [])]

    out = []
    for tid, score in ranked[:k]:
        m = store.meta.get(tid, {})
        out.append({
            "id": tid,
            "score": score,
            "title": m.get("title") or tid,
            "artists": m.get("artist_names") or m.get("artists"),
            "year": m.get("year"),
            "pop_bucket": m.get("pop_bucket"),
            "genres": m.get("genres"),
        })
    return out

# -------- Multi-seed entry --------
def _gather_vectors(store: FileStore, track_ids: List[str]) -> List[np.ndarray]:
    vs = []
    for tid in track_ids:
        v = store.vector(tid)
        if v is not None:
            vs.append(v)
    return vs

def recommend_from_seeds(
    track_ids: List[str],
    k: int = 25,
    bucket_bias: float = 1.0,
    require_genre: str | None = None,
) -> List[dict]:
    # load store once
    store = recommend_from_file._store  # type: ignore[attr-defined]
    if store is None:
        store = FileStore.load()
        recommend_from_file._store = store  # type: ignore[attr-defined]

    seeds = [_norm_id(x) for x in track_ids if x]
    if not seeds:
        return []

    # centroid of normalized vectors
    vs = _gather_vectors(store, seeds)
    if not vs:
        return []
    V = np.stack(vs, axis=0).astype(np.float32)
    Vn = V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-8)
    q = Vn.mean(axis=0)
    q = q / (np.linalg.norm(q) + 1e-8)

    raw = _cosine_knn(q, store.vecs, store.ids, top_k=max(k * 6, 60))
    raw = [(tid, s) for (tid, s) in raw if tid not in set(seeds)]

    # aggregated profile across all seeds
    metas = [store.meta.get(t, {}) for t in seeds]
    profile = _make_profile(metas)

    ranked = _rerank_with_profile(raw, store, profile, boost=bucket_bias)

    if require_genre:
        rg = require_genre.lower().strip()
        ranked = [(tid, s) for (tid, s) in ranked if rg in (store.meta.get(tid, {}).get("genres") or [])]

    out = []
    for tid, score in ranked[:k]:
        m = store.meta.get(tid, {})
        out.append({
            "id": tid,
            "score": score,
            "title": m.get("title") or tid,
            "artists": m.get("artist_names") or m.get("artists"),
            "year": m.get("year"),
            "pop_bucket": m.get("pop_bucket"),
            "genres": m.get("genres"),
        })
    return out

# keep the cache attr
recommend_from_file._store = None  # type: ignore[attr-defined]