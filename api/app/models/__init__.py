from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from ..config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.database_url.startswith("sqlite")

# SQLite serves blocking DB work from a threadpool, so it needs the cross-thread setting.
# The Postgres path opens/closes a connection per request (NullPool) so an idle service
# holds no warm connection and can scale to zero.
_engine_kwargs = (
    {"connect_args": {"check_same_thread": False}} if _is_sqlite else {"poolclass": NullPool}
)
engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create the schema directly from the models. Used by the test suite, whose database
    is disposable; the real dev/prod databases are evolved with Alembic (`alembic upgrade head`)."""
    from . import item  # noqa: F401 — import to register the model on Base.metadata

    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a session, commit on success, roll back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
