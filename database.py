import os

try:
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
except Exception:  # pragma: no cover
    create_engine = None
    declarative_base = None
    sessionmaker = None

# Use environment variable for Docker, fallback to sqlite for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

if create_engine is not None:
    connect_args = {}
    if "sqlite" in DATABASE_URL:
        connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
else:
    engine = None
    SessionLocal = None
    Base = None

def get_db():
    # SQLAlchemy path
    if SessionLocal is not None:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
        return

    # Minimal sqlite3 fallback
    import sqlite3

    if not DATABASE_URL.startswith("sqlite:"):
        yield None
        return

    path = DATABASE_URL.split("sqlite:///", 1)[-1]
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()