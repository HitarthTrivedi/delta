from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

database_url = settings.DATABASE_URL
if database_url.startswith("sqlite+aiosqlite://"):
    database_url = database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)

is_sqlite = database_url.startswith("sqlite")
# Postgres (psycopg 3): no server-side prepared statements, which break behind
# Supabase's transaction-mode pooler (port 6543). Harmless on direct/session connections.
connect_args = {"check_same_thread": False} if is_sqlite else {"prepare_threshold": None}

# pool_pre_ping drops dead connections before use. For Postgres the pool size
# comes from config: Supabase caps total connections per project, so keep
# (pool_size + max_overflow) x processes under that cap. SQLite ignores pool
# sizing (single file connection).
engine_kwargs = {
    "connect_args": connect_args,
    "echo": settings.SQL_ECHO,
    "pool_pre_ping": True,
}
if not is_sqlite:
    engine_kwargs.update(pool_size=settings.DB_POOL_SIZE, max_overflow=settings.DB_MAX_OVERFLOW, pool_recycle=1800)

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
