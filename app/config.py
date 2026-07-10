import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


def _default_data_dir() -> Path:
    """Resolve data/ on local dev and Vercel serverless (/var/task)."""
    env = os.environ.get("DATA_DIR")
    if env:
        return Path(env)
    for candidate in (_ROOT / "data", Path.cwd() / "data"):
        if candidate.is_dir():
            return candidate
    return _ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sindibad"
    app_version: str = "0.1.0"
    data_dir: Path = _default_data_dir()
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    default_language: str = "en"
    openai_api_key: str | None = None


settings = Settings()
