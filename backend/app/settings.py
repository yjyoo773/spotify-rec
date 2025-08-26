from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    SPOTIFY_CLIENT_ID: str | None = None
    SPOTIFY_CLIENT_SECRET: str | None = None
    SPOTIFY_REDIRECT_URI: str | None = None

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/spotify_recs"
    REDIS_URL: str = "redis://redis:6379/0"

    CATALOG_PATH: str = "/app/app/data/catalog.csv"
    GENRE_PATH: str = "/app/app/data/artist_genres.csv"
    POP_SPLIT: int = 10
    VECTOR_DIM: int = 128

    # ✅ new Pydantic v2 style
    model_config = ConfigDict(env_file=".env")


settings = Settings()
