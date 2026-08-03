import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from ..config import settings


class Base(DeclarativeBase):
    pass


# The configured URL is the logical, sync-dialect URL (`sqlite:///`, `postgresql://`) — the
# same value migrations/env.py drives its own sync engine from. The async runtime engine maps
# it onto the matching async DBAPI (aiosqlite for dev/tests, asyncpg for Postgres), so invariant
# 6 holds: the backend is chosen by the URL's dialect, never by an environment name.
def _async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + url[len("sqlite://") :]
    return url


# NullPool across both dialects: a connection is never held across the table-creation loop
# (init_db) and the request loop, and Postgres still opens/closes a connection per request so
# an idle service holds none and scales to zero.
engine = create_async_engine(_async_database_url(settings.database_url), poolclass=NullPool)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create the schema directly from the models. Used by the test suite, whose database
    is disposable; the real dev/prod databases are evolved with Alembic (`alembic upgrade head`)."""
    from . import item  # noqa: F401 — import to register the model on Base.metadata

    # Sync entry point: the suite calls it at import time. Under NullPool the connection opened
    # here is discarded, so driving the async engine's DDL through a throwaway loop is safe.
    asyncio.run(_create_all())


async def _create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a session, commit on success, roll back on error."""
    db = SessionLocal()
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
