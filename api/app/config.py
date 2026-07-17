from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NAGARA_", env_file=".env", extra="ignore")

    api_key: str = "dev-key-nagara"
    default_voice: str = "af_heart"
    data_dir: Path = _DEFAULT_DATA_DIR
    database_url: str = ""
    modal_app: str = "nagara-tts"
    modal_cls: str = "Kokoro"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @model_validator(mode="after")
    def _derive(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"sqlite:///{self.data_dir}/nagara.db"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        return self


settings = Settings()
