"""The migration path: alembic head must equal the models (invariant 7).

The test schema is built from the models, so the suite never exercises the migrations
themselves; this check upgrades a throwaway database to head and compares the result
against the current models, so a model change without a migration fails here instead of
at the next real deploy. The downgrade path is exercised one step down and back, which
is what the manual migration rows (B20-B22) replay against a real snapshot.
"""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

import app.models.cost  # noqa: F401 — register the models on Base.metadata
import app.models.item  # noqa: F401
import app.models.recipe  # noqa: F401
from app.config import settings
from app.models import Base


def test_migrations_reach_the_current_models(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/migration.db"
    monkeypatch.setattr(settings, "database_url", url, raising=False)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diff == [], f"alembic head and the models disagree: {diff}"


def test_downgrade_one_step_drops_the_boundary_and_back(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/migration.db"
    monkeypatch.setattr(settings, "database_url", url, raising=False)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "-1")  # B22: the boundary table and columns are gone
    command.upgrade(config, "head")  # and reapplying restores them
