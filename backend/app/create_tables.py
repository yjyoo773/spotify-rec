from .db import engine
from .models import Base
from sqlalchemy import text

def create_all():
    Base.metadata.create_all(bind=engine)
    # create vector extension if needed (will be noop if already exists)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

if __name__ == "__main__":
    create_all()
    print("Tables created.")