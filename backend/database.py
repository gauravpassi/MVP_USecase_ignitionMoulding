from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL, DB_MODE

connect_args = {}
if DB_MODE == "sqlite":
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, pool_pre_ping=(DB_MODE == "postgres"), connect_args=connect_args)

# Enable WAL mode for SQLite (better concurrent reads)
if DB_MODE == "sqlite":
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from backend.models import db_models  # noqa: F401 — registers models
    Base.metadata.create_all(bind=engine)
