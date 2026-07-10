from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sindibad"
    app_version: str = "0.1.0"
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    default_language: str = "en"
    openai_api_key: str | None = None


settings = Settings()
