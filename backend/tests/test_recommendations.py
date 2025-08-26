# backend/tests/test_recommendations.py
import pandas as pd
from app.recommender import recommend

def test_recommend_tracks():
    # Fake catalog of tracks
    catalog_df = pd.DataFrame({
        "id": ["t1", "t2", "t3"],
        "feature1": [0.1, 0.2, 0.3],
        "feature2": [0.5, 0.4, 0.6]
    })

    # Playlist vector (average of tracks)
    playlist_vec = pd.Series({"feature1": 0.15, "feature2": 0.45})

    # Non-playlist features
    nonplaylist_features = pd.DataFrame({
        "id": ["t4", "t5"],
        "feature1": [0.1, 0.3],
        "feature2": [0.5, 0.7]
    })

    # Call function
    results = recommend.recommend_tracks(catalog_df, playlist_vec, nonplaylist_features, top_k=2)

    assert not results.empty
    assert len(results) <= 2
    assert "sim" in results.columns
