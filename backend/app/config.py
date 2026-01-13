"""Application configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE_BACKEND = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_BACKEND),
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://sigdig:sigdig_dev@localhost:5432/sigdig"

    # AI Services
    google_api_key: str = ""
    ai_run_timeout_seconds: int = 900
    ai_classification_timeout_seconds: int = 60
    ai_extraction_timeout_seconds: int = 90

    # Video Extraction
    video_extraction_enabled: bool = True
    video_extraction_timeout_seconds: int = 90

    # Social Media APIs
    twitter_api_key: str = ""
    youtube_data_api_key: str = ""
    tavily_api_key: str = ""
    tavily_search_depth: str = "advanced"

    # Application
    app_env: str = "development"


settings = Settings()
