import pandas as pd

def playlist_vector(complete_features: pd.DataFrame, playlist_df: pd.DataFrame, weight_factor: float = 1.15):
    cf = complete_features.copy().reset_index(drop=True)
    pl = playlist_df.copy().rename(columns={"added_at":"date_added","date_added":"date_added"}).reset_index(drop=True)
    merged = cf[cf["id"].isin(pl["id"].values)].merge(pl[["id","date_added"]], on="id", how="inner")
    if merged.empty:
        return None, cf[~cf["id"].isin(pl["id"].values)]
    merged = merged.sort_values("date_added", ascending=False)
    most_recent = pd.to_datetime(merged["date_added"]).max()
    months_from_recent = (pd.to_datetime(most_recent) - pd.to_datetime(merged["date_added"])).dt.days // 30
    weights = (weight_factor ** (-months_from_recent)).astype(float).values
    feature_cols = [c for c in merged.columns if c not in ("id","date_added")]
    weighted = merged[feature_cols].multiply(weights, axis=0).sum(axis=0)
    nonplaylist = cf[~cf["id"].isin(merged["id"].values)].reset_index(drop=True)
    return weighted, nonplaylist