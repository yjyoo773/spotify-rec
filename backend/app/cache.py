import redis
import os
import json
from typing import Any, Optional

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

def set_cache(key: str, value: Any, ttl: int = 600):
    r.setex(key, ttl, json.dumps(value))

def get_cache(key: str) -> Optional[Any]:
    v = r.get(key)
    if not v:
        return None
    return json.loads(v)

def make_playlist_snapshot_key(owner_id: str, playlist_id: str, snapshot_id: str):
    return f"playlist_snapshot:{owner_id}:{playlist_id}:{snapshot_id}"