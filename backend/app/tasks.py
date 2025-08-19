from rq import Queue
from redis import Redis
import os
import pandas as pd
from datetime import datetime
from .recommender.data_prep import data_prep
from .recommender.feature_engineering import create_feature_set
from .db import SessionLocal
from .models import Track, TrackFeature

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
q = Queue("default", connection=redis_conn)

def refresh_catalog_task(catalog_path: str, genre_path: str, pop_split: int):
    catalog_df = pd.read_csv(catalog_path)
    genre_df = pd.read_csv(genre_path)
    catalog_df = data_prep(catalog_df, genre_df, pop_split)
    features_df = create_feature_set(catalog_df)
    with SessionLocal() as session:
        for _, row in catalog_df.iterrows():
            t = session.get(Track, row['id'])
            if not t:
                t = Track(id=row['id'], name=row.get('name'), artists=[], release_date=row.get('release_date'), popularity=int(row.get('popularity',0)), meta={})
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
    return {"status":"ok", "updated": len(catalog_df)}

def schedule_refresh(catalog_path: str, genre_path: str, pop_split: int):
    job = q.enqueue(refresh_catalog_task, catalog_path, genre_path, pop_split)
    return job.id