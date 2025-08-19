from typing import List, Dict
import pandas as pd
from .feature_engineering import create_feature_set
from ..spotify_client import get_audio_features, get_artist
from datetime import datetime
from ..db import SessionLocal
from ..models import Track, TrackFeature
import json

def build_on_the_fly_features(access_token: str, track_ids: List[str], artist_ids_map: Dict[str, List[str]]):
    audio_feats = get_audio_features(access_token, track_ids)
    audio_by_id = {a['id']: a for a in audio_feats if a}
    rows = []
    for tid in track_ids:
        af = audio_by_id.get(tid, {})
        artist_ids = artist_ids_map.get(tid, [])
        genres = []
        for aid in artist_ids:
            if not aid:
                continue
            artist = get_artist(access_token, aid)
            g = artist.get("genres", [])
            if g:
                genres.extend([s.replace(" ", "_") for s in g])
        row = {
            "id": tid,
            "name": af.get("id", tid),
            "artists": json.dumps([]),
            "release_date": af.get("release_date", ""),
            "popularity": af.get("popularity", 0),
            "danceability": af.get("danceability", 0.0),
            "energy": af.get("energy", 0.0),
            "loudness": af.get("loudness", 0.0),
            "speechiness": af.get("speechiness", 0.0),
            "acousticness": af.get("acousticness", 0.0),
            "instrumentalness": af.get("instrumentalness", 0.0),
            "liveness": af.get("liveness", 0.0),
            "valence": af.get("valence", 0.0),
            "tempo": af.get("tempo", 0.0),
            "consolidate_genre_lists": genres
        }
        rows.append(row)
    tmp_df = pd.DataFrame(rows)
    features_df = create_feature_set(tmp_df)
    # persist minimal track & feature records
    with SessionLocal() as session:
        for _, r in tmp_df.iterrows():
            t = session.get(Track, r['id'])
            if not t:
                t = Track(id=r['id'], name=r.get('name'), artists=[], release_date=r.get('release_date'), popularity=int(r.get('popularity',0)), meta={})
                session.add(t)
        session.commit()
        for _, fr in features_df.iterrows():
            fid = fr['id']
            feature_cols = [c for c in features_df.columns if c != 'id']
            tf = session.get(TrackFeature, fid)
            features_json = fr[feature_cols].to_dict()
            if not tf:
                tf = TrackFeature(id=fid, features=features_json, last_updated=datetime.utcnow())
                session.add(tf)
            else:
                tf.features = features_json
                tf.last_updated = datetime.utcnow()
        session.commit()
    return features_df
