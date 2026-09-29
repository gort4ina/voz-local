from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[3] / ".env", ".env"), extra="ignore"
    )
    database_url: str = "sqlite:///./data/voz.db"
    upload_dir: Path = Path("./data/uploads")
    max_audio_size_mb: int = Field(default=512, ge=1, le=4096)
    max_audio_duration_seconds: int = Field(default=7200, ge=1, le=28800)
    default_language: str = "pt"
    cors_origins: list[str] = ["http://localhost:4200", "http://localhost:8080"]
    whisper_model: str = "small"
    whisper_device: Literal["auto", "cpu", "cuda"] = "auto"
    whisper_compute_type: str = "auto"
    diarization_device: Literal["auto", "cpu", "cuda"] = "auto"
    diarization_model: str = "pyannote/speaker-diarization-community-1"
    hf_home: Path = Path("./models-cache")
    huggingface_token: SecretStr = SecretStr("")
    job_lease_seconds: int = Field(default=180, ge=30)
    job_max_attempts: int = Field(default=3, ge=1)
    retention_days: int = Field(default=0, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
