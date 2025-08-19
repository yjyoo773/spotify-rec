import requests, time, math
from typing import List, Dict, Optional
from .settings import settings

SPOTIFY_API = "https://api.spotify.com/v1"

def _headers(access_token: str):
    return {"Authorization": f"Bearer {access_token}"}

def _request_with_backoff(method: str, url: str, headers=None, params=None, json=None, max_retries=6, backoff_base=0.8):
    attempt = 0
    while True:
        resp = requests.request(method, url, headers=headers, params=params, json=json)
        if resp.status_code == 429:
            attempt += 1
            if attempt > max_retries:
                resp.raise_for_status()
            retry_after = int(resp.headers.get("Retry-After", math.ceil(backoff_base * (2 ** attempt))))
            time.sleep(retry_after)
            continue
        if resp.status_code >= 500 and attempt < max_retries:
            attempt += 1
            time.sleep(backoff_base * (2 ** attempt))
            continue
        resp.raise_for_status()
        return resp

def get_playlist(access_token: str, playlist_id: str) -> Dict:
    url = f"{SPOTIFY_API}/playlists/{playlist_id}"
    resp = _request_with_backoff("GET", url, headers=_headers(access_token))
    return resp.json()

def get_playlist_tracks(access_token: str, playlist_id: str) -> List[Dict]:
    url = f"{SPOTIFY_API}/playlists/{playlist_id}/tracks"
    params = {"limit": 100}
    items = []
    while url:
        resp = _request_with_backoff("GET", url, headers=_headers(access_token), params=params)
        data = resp.json()
        items.extend(data.get("items", []))
        url = data.get("next")
        params = None
    out = []
    latest_snapshot = None
    for it in items:
        latest_snapshot = it.get("snapshot_id", latest_snapshot)
        t = it.get("track")
        if not t or t.get("id") is None:
            continue
        out.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "artists": [a["name"] for a in t.get("artists", [])],
            "artist_ids": [a.get("id") for a in t.get("artists", []) if a.get("id")],
            "added_at": it.get("added_at"),
            "snapshot_id": latest_snapshot
        })
    return out

def get_audio_features(access_token: str, ids: List[str]) -> List[Optional[Dict]]:
    out = []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i+100]
        url = f"{SPOTIFY_API}/audio-features"
        resp = _request_with_backoff("GET", url, headers=_headers(access_token), params={"ids": ",".join(chunk)})
        out.extend(resp.json().get("audio_features", []))
    return out

def get_artist(access_token: str, artist_id: str) -> Dict:
    url = f"{SPOTIFY_API}/artists/{artist_id}"
    resp = _request_with_backoff("GET", url, headers=_headers(access_token))
    return resp.json()

def get_tracks_batch(access_token: str, ids: List[str]) -> List[Dict]:
    out = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        url = f"{SPOTIFY_API}/tracks"
        resp = _request_with_backoff("GET", url, headers=_headers(access_token), params={"ids": ",".join(chunk)})
        out.extend(resp.json().get("tracks", []))
    return out

def add_tracks_to_playlist(access_token: str, playlist_id: str, uris: List[str]) -> Dict:
    url = f"{SPOTIFY_API}/playlists/{playlist_id}/tracks"
    resp = _request_with_backoff("POST", url, headers={**_headers(access_token), "Content-Type":"application/json"}, json={"uris": uris})
    return resp.json()
