from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
import os, pickle, math
import numpy as np

# ---------- Paths (env-configurable; defaults to app/data/*) ----------
THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(THIS_DIR), "data"))
FEATURES_PATH = os.environ.get("FEATURES_PATH", os.path.join(DATA_DIR, "features.npz"))
META_PATH = os.environ.get("META_PATH", os.path.join(DATA_DIR, "meta.pkl"))

# ---------- Small utils ----------

def _norm_id(x: str) -> str:
    """
    Accept raw Spotify IDs, track URIs (spotify:track:ID), or https URLs.
    Returns bare ID string.
    """
    s = (x or "").strip()
    if not s:
        return s
    # spotify:track:ID
    if s.startswith("spotify:"):
        parts = s.split(":")
        return parts[-1]
    # https://open.spotify.com/track/ID?si=...
    if s.startswith("http"):
        try:
            from urllib.parse import urlparse
            p = urlparse(s)
            # path like /track/ID
            segs = [seg for seg in p.path.split("/") if seg]
            if segs and segs[0] == "track" and len(segs) >= 2:
                return segs[1]
        except Exception:
            pass
    return s

def _primary_artist(meta: dict) -> Optional[str]:
    # meta["artist_names"] is set by your build script; fall back to artists if present
    arts = meta.get("artist_names") or meta.get("artists") or []
    return arts[0] if isinstance(arts, list) and arts else None

def _sigmoid(x: float, k: float = 0.08, x0: float = 50.0) -> float:
    # used sparingly on popularity (bucket proximity also used)
    return 1.0 / (1.0 + math.exp(-k * (float(x) - x0)))

# ---------- Vector store ----------

@dataclass
class FileStore:
    ids: np.ndarray          # shape (N,), dtype=object/str
    vecs: np.ndarray         # shape (N, D), float32, L2-normalized
    meta: Dict[str, dict]    # track_id -> meta

    id_to_row: Dict[str, int]

    @classmethod
    def load(cls) -> "FileStore":
        if not os.path.exists(FEATURES_PATH):
            raise FileNotFoundError(f"FEATURES_PATH not found: {FEATURES_PATH}")
        if not os.path.exists(META_PATH):
            raise FileNotFoundError(f"META_PATH not found: {META_PATH}")

        npz = np.load(FEATURES_PATH, allow_pickle=True)
        ids = npz["ids"]
        vecs = npz["vecs"].astype(np.float32)
        # safety: L2 normalize
        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
        vecs = vecs / norms

        with open(META_PATH, "rb") as f:
            meta = pickle.load(f)

        # normalize keys to str and build index
        ids = np.array([str(i) for i in ids], dtype=object)
        id_to_row = {str(tid): i for i, tid in enumerate(ids)}
        return cls(ids=ids, vecs=vecs, meta=meta, id_to_row=id_to_row)

    def vector(self, tid: str) -> Optional[np.ndarray]:
        r = self.id_to_row.get(str(tid))
        if r is None:
            return None
        return self.vecs[r]

# Lazy singletons for perf (kept compatible with your current code)
_store_singleton: Optional[FileStore] = None

def _store() -> FileStore:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = FileStore.load()
    return _store_singleton

# ---------- Core math ----------

def _cosine_knn(q: np.ndarray, V: np.ndarray, ids: np.ndarray, top_k: int = 2000) -> List[Tuple[str, float]]:
    """
    Compute cosine similarity to all vectors (file-backed dense matrix), return top_k (id, score).
    Assumes q and V are L2-normalized.
    """
    sims = V @ q.astype(np.float32)
    top_k = min(int(top_k), sims.shape[0])
    if top_k <= 0:
        return []
    idx = np.argpartition(sims, -top_k)[-top_k:]
    idx = idx[np.argsort(sims[idx])[::-1]]
    return [(str(ids[i]), float(sims[i])) for i in idx]

def _mean_vector(store: FileStore, track_ids: List[str]) -> Optional[np.ndarray]:
    vecs = []
    for raw in track_ids:
        tid = _norm_id(raw)
        v = store.vector(tid)
        if v is not None:
            vecs.append(v.astype(np.float32))
    if not vecs:
        return None
    m = np.mean(vecs, axis=0)
    n = np.linalg.norm(m) + 1e-12
    return (m / n).astype(np.float32)

# ---------- Era filter & bucket sampler ----------

def _filter_by_year(store: FileStore, cands: List[Tuple[str, float]], q_year: Optional[int], target: int) -> List[Tuple[str, float]]:
    """
    Keep candidates near query year; progressively widen until target count or give up.
    """
    if q_year is None:
        return cands
    widths = [4, 6, 8, 10, 12, 20, None]  # ~ tight → looser
    for w in widths:
        if w is None:
            return cands
        kept: List[Tuple[str, float]] = []
        for tid, s in cands:
            y = store.meta.get(tid, {}).get("year")
            try:
                y = int(y)
            except Exception:
                y = None
            if y is not None and abs(int(q_year) - y) <= w:
                kept.append((tid, s))
        if len(kept) >= min(target, max(50, len(cands)//3)):
            return kept
    return cands

def _bucket_sample(store: FileStore, cands: List[Tuple[str, float]], k: int, bias: float = 0.5) -> List[Tuple[str, float]]:
    """
    Compose a shortlist by popularity bucket.
    bias:
      1.0 -> proportional to bucket size
      0.0 -> flatten buckets (each equal weight)
     -0.5 -> gently favor smaller buckets
    """
    from collections import defaultdict
    by_bucket = defaultdict(list)
    for tid, s in cands:
        b = store.meta.get(tid, {}).get("pop_bucket")
        try:
            b = int(b)
        except Exception:
            b = -1
        by_bucket[b].append((tid, s))

    counts = {b: len(v) for b, v in by_bucket.items()}
    if not counts:
        return cands[:k]

    buckets = list(counts.keys())
    weights = np.array([(counts[b] ** bias) for b in buckets], dtype=float)
    weights = weights / (weights.sum() + 1e-9)
    take = (weights * k).round().astype(int)

    out: List[Tuple[str, float]] = []
    rng = np.random.default_rng(42)
    for b, n in zip(buckets, take):
        pool = by_bucket[b]
        if not pool:
            continue
        n = int(min(n, len(pool)))
        if n <= 0:
            continue
        idx = rng.choice(len(pool), size=n, replace=False)
        out.extend([pool[i] for i in idx])

    # top-up if rounding underfills
    if len(out) < k:
        rest = sorted(cands, key=lambda p: p[1], reverse=True)
        seen = {tid for tid, _ in out}
        for tid, s in rest:
            if tid not in seen:
                out.append((tid, s))
                seen.add(tid)
            if len(out) >= k:
                break
    return out[:k]

# ---------- Profile & rerank ----------

def _make_profile(metas: List[dict]) -> dict:
    years = []
    pops = []
    seed_artists: Set[str] = set()
    for m in metas:
        y = m.get("year")
        try:
            years.append(int(y))
        except Exception:
            pass
        p = m.get("pop_bucket")
        try:
            pops.append(int(p))
        except Exception:
            pass
        a = _primary_artist(m)
        if a:
            seed_artists.add(a)
    prof = {
        "year": int(np.median(years)) if years else None,
        "pop_bucket": int(np.median(pops)) if pops else None,
        "seed_artists": seed_artists,
    }
    return prof

def _rerank_with_profile(cands: List[Tuple[str, float]], store: FileStore, profile: dict, boost: float = 1.0) -> List[Tuple[str, float]]:
    """
    Final score = cosine + priors; also lightly de-duplicate by primary artist.
    """
    q_year = profile.get("year")
    q_pop = profile.get("pop_bucket")
    seed_artists: Set[str] = profile.get("seed_artists") or set()

    def year_prior(y) -> float:
        if q_year is None or y is None:
            return 0.0
        try:
            y = int(y)
        except Exception:
            return 0.0
        # Gaussian with σ ~ 3.5 years
        return float(np.exp(-((y - int(q_year))**2) / (2 * 3.5**2)))

    def pop_close(p) -> float:
        if q_pop is None or p is None:
            return 0.0
        try:
            gap = abs(int(p) - int(q_pop))
        except Exception:
            return 0.0
        return max(0.0, 1.0 - min(gap, 10) / 10.0)

    def bonus(tid: str) -> float:
        m = store.meta.get(tid, {})
        b = 0.0
        b += 0.15 * year_prior(m.get("year"))
        b += 0.05 * pop_close(m.get("pop_bucket"))
        # light artist diversity: nudge down repeats
        if _primary_artist(m) in seed_artists:
            b -= 0.06
        return b * boost

    ranked = sorted(cands, key=lambda p: p[1] + bonus(p[0]), reverse=True)

    # light artist-level MMR (single-pass demotion)
    seen_primary: Set[str] = set()
    out: List[Tuple[str, float]] = []
    for tid, s in ranked:
        a = _primary_artist(store.meta.get(tid, {}))
        if a and a in seen_primary:
            out.append((tid, s - 0.02))
        else:
            out.append((tid, s))
            if a:
                seen_primary.add(a)
    return out

# ---------- Public API (used by app.main) ----------

def recommend_from_file(track_id: str, k: int = 25, bucket_bias: float = 1.0, require_genre: Optional[str] = None) -> List[dict]:
    """
    Single-seed recommendation from file-backed features.
    - Audio-feature cosine → high recall
    - Year prefilter → era consistency
    - Bucket sampler → mix control (via bucket_bias)
    - Rerank with priors + diversity
    """
    store = _store()
    tid = _norm_id(track_id)
    q = store.vector(tid)
    if q is None:
        return []

    # high-recall ANN
    raw = _cosine_knn(q, store.vecs, store.ids, top_k=max(k * 80, 2000))
    raw = [(t, s) for (t, s) in raw if t != tid]

    # build profile from this seed
    profile = _make_profile([store.meta.get(tid, {})])

    # era shaping before sampling
    raw = _filter_by_year(store, raw, profile.get("year"), target=max(k * 20, 1000))
    # compose shortlist with bucket bias
    raw = _bucket_sample(store, raw, k=max(k * 10, 300), bias=bucket_bias)
    # rerank with priors + diversity
    ranked = _rerank_with_profile(raw, store, profile, boost=1.0)

    if require_genre:
        # retained for compatibility; genres are mostly empty in your data, so this usually is a no-op
        g = require_genre.lower().strip()
        ranked = [(t, s) for (t, s) in ranked if g in (store.meta.get(t, {}).get("genres") or [])]

    out: List[dict] = []
    for t, score in ranked[:k]:
        m = store.meta.get(t, {})
        out.append({
            "id": t,
            "score": float(score),
            "title": m.get("title") or t,
            "artists": m.get("artist_names") or m.get("artists"),
            "year": m.get("year"),
            "pop_bucket": m.get("pop_bucket"),
            "genres": m.get("genres"),
        })
    return out

def recommend_from_seeds(track_ids: List[str], k: int = 25, bucket_bias: float = 1.0, require_genre: Optional[str] = None) -> List[dict]:
    """
    Multi-seed recommendation:
    - Mean of available seed vectors (L2-normalized)
    - Same pipeline as single-seed
    """
    store = _store()
    seeds = [ _norm_id(t) for t in track_ids if _norm_id(t) ]
    q = _mean_vector(store, seeds)
    if q is None:
        return []

    raw = _cosine_knn(q, store.vecs, store.ids, top_k=max(k * 80, 2000))
    raw = [(t, s) for (t, s) in raw if t not in set(seeds)]

    metas = [store.meta.get(t, {}) for t in seeds]
    profile = _make_profile(metas)

    raw = _filter_by_year(store, raw, profile.get("year"), target=max(k * 20, 1000))
    raw = _bucket_sample(store, raw, k=max(k * 10, 300), bias=bucket_bias)
    ranked = _rerank_with_profile(raw, store, profile, boost=1.0)

    if require_genre:
        g = require_genre.lower().strip()
        ranked = [(t, s) for (t, s) in ranked if g in (store.meta.get(t, {}).get("genres") or [])]

    out: List[dict] = []
    for t, score in ranked[:k]:
        m = store.meta.get(t, {})
        out.append({
            "id": t,
            "score": float(score),
            "title": m.get("title") or t,
            "artists": m.get("artist_names") or m.get("artists"),
            "year": m.get("year"),
            "pop_bucket": m.get("pop_bucket"),
            "genres": m.get("genres"),
        })
    return out