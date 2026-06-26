from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

database_url = settings.DATABASE_URL
if database_url.startswith("sqlite+aiosqlite://"):
    database_url = database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)

is_sqlite = database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# pool_pre_ping drops dead connections before use. For server databases
# (Postgres on Render) size the pool so concurrent requests don't queue;
# SQLite ignores pool sizing (single file connection).
engine_kwargs = {
    "connect_args": connect_args,
    "echo": settings.SQL_ECHO,
    "pool_pre_ping": True,
}
if not is_sqlite:
    engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=1800)

engine = create_engine(database_url, **engine_kwargs)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        """WAL lets readers run concurrently with a writer; busy_timeout makes
        writers wait briefly instead of failing under concurrent load."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
