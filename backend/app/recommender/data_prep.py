# (copy the version from earlier in conversation)
from __future__ import annotations
import pandas as pd
import numpy as np
import re
import itertools

def normalize_genre(genre_df: pd.DataFrame) -> pd.DataFrame:
    df = genre_df.copy()
    df["genres_upd"] = df["genres"].apply(lambda x: [re.sub(r"\s+", "_", i) for i in re.findall(r"'([^']*)'", x)] if isinstance(x, str) else [])
    return df

def normalize_artists(spotify_df: pd.DataFrame) -> pd.DataFrame:
    df = spotify_df.copy()
    v1 = df["artists"].apply(lambda x: re.findall(r"'([^']*)'", x) if isinstance(x, str) else [])
    v2 = df["artists"].apply(lambda x: re.findall(r"\"(.*?)\"", x) if isinstance(x, str) else [])
    df["artists_final"] = np.where(v1.apply(len).eq(0), v2, v1)
    return df

def song_artist_identifier(spotify_df: pd.DataFrame) -> pd.DataFrame:
    df = spotify_df.copy()
    df["artist_song"] = df.apply(lambda r: f"{(r['artists_final'][0] if isinstance(r['artists_final'], list) and r['artists_final'] else 'unknown')}_{r['name']}", axis=1)
    df = df.drop_duplicates("artist_song")
    return df

def combine_dataframes(spotify_df: pd.DataFrame, genre_df: pd.DataFrame) -> pd.DataFrame:
    df = spotify_df.copy()
    exploded = df[["artists_final", "id"]].explode("artists_final")
    merged = exploded.merge(genre_df, how="left", left_on="artists_final", right_on="artists")
    merged_nonnull = merged[merged["genres_upd"].notna()]
    by_song = merged_nonnull.groupby("id")["genres_upd"].apply(list).reset_index()
    by_song["consolidate_genre_lists"] = by_song["genres_upd"].apply(lambda x: list(set(itertools.chain.from_iterable(x))))
    return df.merge(by_song[["id", "consolidate_genre_lists"]], on="id", how="left")

def split_pop_year(spotify_df: pd.DataFrame, pop_split: int) -> pd.DataFrame:
    df = spotify_df.copy()
    df["year"] = df["release_date"].astype(str).str.split("-").str[0]
    df["pop_red"] = df["popularity"].fillna(0).astype(int).floordiv(pop_split)
    df["consolidate_genre_lists"] = df["consolidate_genre_lists"].apply(lambda x: x if isinstance(x, list) else [])
    return df

def data_prep(spotify_df: pd.DataFrame, genre_df: pd.DataFrame, pop_split: int) -> pd.DataFrame:
    genre_df = normalize_genre(genre_df)
    df = normalize_artists(spotify_df)
    df = song_artist_identifier(df)
    df = combine_dataframes(df, genre_df)
    return split_pop_year(df, pop_split)