from __future__ import annotations
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler

YEAR_SCALER = 0.5
POPULARITY_SCALER = 0.15
FLOAT_SCALER = 0.2

def _ohe(df: pd.DataFrame, col: str, prefix: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame(index=df.index)
    tf = pd.get_dummies(df[col].astype(str))
    tf.columns = [f"{prefix}|{c}" for c in tf.columns]
    return tf.reset_index(drop=True)

def create_feature_set(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().reset_index(drop=True)
    tfidf = TfidfVectorizer()
    genre_corpus = df["consolidate_genre_lists"].apply(lambda xs: " ".join(xs) if isinstance(xs, list) else "")
    tfidf_matrix = tfidf.fit_transform(genre_corpus)
    genre_cols = [f"genre|{c}" for c in tfidf.get_feature_names_out()]
    genre_df = pd.DataFrame(tfidf_matrix.toarray(), columns=genre_cols).reset_index(drop=True)

    year_ohe = _ohe(df, "year", "year") * YEAR_SCALER
    pop_ohe  = _ohe(df, "pop_red", "pop") * POPULARITY_SCALER

    numeric = df.select_dtypes(include="number").copy()
    if not numeric.empty:
        scaler = MinMaxScaler()
        floats_scaled = pd.DataFrame(scaler.fit_transform(numeric), columns=numeric.columns) * FLOAT_SCALER
    else:
        floats_scaled = pd.DataFrame()

    final = pd.concat([genre_df.reset_index(drop=True), floats_scaled.reset_index(drop=True), pop_ohe.reset_index(drop=True), year_ohe.reset_index(drop=True)], axis=1).fillna(0)
    final["id"] = df["id"].values
    return final