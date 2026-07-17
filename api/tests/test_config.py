from app.config import Settings


def test_normalizes_legacy_postgres_scheme():
    assert Settings(database_url="postgres://u:p@host/db").database_url == "postgresql://u:p@host/db"


def test_keeps_postgresql_scheme():
    assert Settings(database_url="postgresql://u:p@host/db").database_url == "postgresql://u:p@host/db"


def test_defaults_to_sqlite_when_unset(tmp_path):
    assert Settings(database_url="", data_dir=tmp_path).database_url.startswith("sqlite:///")


def test_s3_configured_requires_all_fields():
    full = Settings(
        s3_endpoint="https://storage.railway.app",
        s3_bucket="b",
        s3_access_key_id="k",
        s3_secret_access_key="s",
    )
    assert full.s3_configured is True

    assert Settings(s3_endpoint="https://storage.railway.app", s3_bucket="b").s3_configured is False
    assert Settings().s3_configured is False
