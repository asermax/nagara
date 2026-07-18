from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NAGARA_", env_file=".env", extra="ignore")

    api_key: str = "dev-key-nagara"
    data_dir: Path = _DEFAULT_DATA_DIR
    database_url: str = ""
    modal_app: str = "nagara-tts"
    modal_cls: str = "Kokoro"

    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "auto"
    s3_url_ttl: int = 3600
    # Railway buckets (and most modern hosts) use virtual-hosted-style URLs; some
    # S3-compatible stores need "path" instead — flip without a code change.
    s3_addressing_style: str = "virtual"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def s3_configured(self) -> bool:
        return bool(self.s3_endpoint and self.s3_bucket and self.s3_access_key_id and self.s3_secret_access_key)

    @model_validator(mode="after")
    def _derive(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"sqlite:///{self.data_dir}/nagara.db"

        # Managed Postgres often hands out the legacy `postgres://` scheme, which SQLAlchemy
        # no longer recognizes; normalize to the dialect it expects.
        if self.database_url.startswith("postgres://"):
            self.database_url = "postgresql://" + self.database_url[len("postgres://") :]

        if not self.s3_configured:
            self.audio_dir.mkdir(parents=True, exist_ok=True)

        return self


settings = Settings()
