from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd

def recommend_tracks(catalog_df: pd.DataFrame, playlist_vec: pd.Series, nonplaylist_features: pd.DataFrame, top_k: int = 40):
    if playlist_vec is None or nonplaylist_features.empty:
        return pd.DataFrame()
    feature_cols = [c for c in nonplaylist_features.columns if c != "id"]
    X = nonplaylist_features[feature_cols].to_numpy(dtype=float)
    v = playlist_vec.to_numpy(dtype=float).reshape(1, -1)
    sims = cosine_similarity(X, v).reshape(-1)
    out = nonplaylist_features.copy()
    out["sim"] = sims
    return out.sort_values("sim", ascending=False).head(top_k)
