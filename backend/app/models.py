from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class Track(Base):
    __tablename__ = "tracks"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    artists = Column(JSON)
    release_date = Column(String)
    popularity = Column(Integer)
    meta = Column(JSON, default={})

class TrackFeature(Base):
    __tablename__ = "track_features"
    id = Column(String, primary_key=True)
    features = Column(JSON)   # numeric features as json
    vec = Column(Vector(768)) # will be updated; adjust dim in .env and migrations
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class VectorIndex(Base):
    __tablename__ = "vectors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String, index=True)
    scope_id = Column(String, index=True)
    vec = Column(Vector(768))
    meta = Column(JSON)
    __table_args__ = (UniqueConstraint("scope", "scope_id", name="u_scope_scopeid"),)