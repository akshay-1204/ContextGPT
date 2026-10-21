"""SQLAlchemy Database Engine and Session Management."""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.app.core.config import settings
from backend.app.core.logging import logger

database_url = settings.DATABASE_URL

# Configure PostgreSQL engine with production connection pooling
connect_args = {}
engine_kwargs = {
    "echo": False,
    "future": True,
}

if database_url.startswith("postgresql") or database_url.startswith("postgres"):
    # PostgreSQL connection pooling optimizations
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })
    engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
elif settings.APP_ENV == "testing" and database_url.startswith("sqlite"):
    # In-memory test runner fallback
    connect_args["check_same_thread"] = False
    engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
else:
    raise ValueError(
        f"ContextGPT is configured for PostgreSQL only. "
        f"Invalid database URL: '{database_url}'. "
        "Please provide a valid postgresql+psycopg:// URL in your .env file."
    )


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and ensures clean closure."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verifies that the database engine can successfully execute a query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        return False
