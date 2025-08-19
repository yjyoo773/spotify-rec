import os
import psycopg2
import json

DATABASE_URL = os.environ.get("DATABASE_URL")

def upsert_track_vector(track_id: str, vector: list, features_json: dict):
    conn = psycopg2.connect(DATABASE_URL)
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO track_features (id, features, vec, last_updated)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET features = EXCLUDED.features, vec = EXCLUDED.vec, last_updated = now()
            """, (track_id, json.dumps(features_json), vector))
    conn.close()