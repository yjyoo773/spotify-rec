from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import os, pickle
import numpy as np

# Paths can be overridden by env; defaults match your repo
THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(THIS_DIR), "data"))  # ../data
FEATURES_PATH = os.environ.get("FEATURES_PATH", os.path.join(DATA_DIR, "features.npz"))
META_PATH = os.environ.get("META_PATH", os.path.join(DATA_DIR, "meta.pkl"))


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

def _rerank_with_bias(cands: List[Tuple[str, float]], store: FileStore, query_id: str, boost: float = 1.0):
    if boost <= 0:
        return cands
    qm = store.meta.get(str(query_id), {})
    q_year, q_pop = qm.get("year"), qm.get("pop_bucket")
    def bonus(tid: str) -> float:
        m = store.meta.get(str(tid), {})
        b = 0.0
        if q_year and m.get("year") == q_year: b += 0.02
        if q_pop and m.get("pop_bucket") == q_pop: b += 0.02
        return b * boost
    return sorted(cands, key=lambda p: p[1] + bonus(p[0]), reverse=True)

def _norm_id(x: str) -> str:
    """
    Accepts:
      - raw ID:              0VjIjW4GlUZAMYd2vXMi3b
      - Spotify URI:         spotify:track:0VjIjW4GlUZAMYd2vXMi3b
      - Spotify URL:         https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b?si=...
    Returns the bare track id.
    """
    s = (x or "").strip()
    if not s:
        return s
    # URI form
    if s.startswith("spotify:"):
        return s.rsplit(":", 1)[-1]
    # URL form
    if "open.spotify.com" in s:
        path = urlparse(s).path  # e.g., /track/<id>
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "track":
            return parts[1]
    # Otherwise assume it's already an ID
    return s

# Public entrypoint used by main.py
def recommend_from_file(track_id: str, k: int = 25, bucket_bias: float = 1.0) -> List[dict]:
    track_id = _norm_id(track_id)
    store = recommend_from_file._store  # type: ignore[attr-defined]
    if store is None:
        # lazy-load on first call, so app startup stays fast
        store = FileStore.load()
        recommend_from_file._store = store  # cache singleton

    v = store.vector(track_id)
    if v is None:
        return []

    raw = _cosine_knn(v, store.vecs, store.ids, top_k=max(k * 5, 50))
    raw = [(tid, s) for (tid, s) in raw if tid != str(track_id)]
    ranked = _rerank_with_bias(raw, store, query_id=str(track_id), boost=bucket_bias)[:k]

    # Attach minimal meta for convenience
    out = []
    for tid, score in ranked:
        m = store.meta.get(tid, {})
        out.append({
            "id": tid,
            "score": score,
            "title": m.get("title") or tid,
            "artists": m.get("artist_names") or m.get("artists"),  # prefer names
        })
    return out

# set the cache attribute
recommend_from_file._store = None  # type: ignore[attr-defined]