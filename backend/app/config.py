"""Application configuration."""
from typing import Literal
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

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic", "gemini", "openrouter"] = "gemini"
    llm_model: str = "gemini-3-flash-preview"
    llm_temperature: float = 0.2

    # LLM API Keys
    google_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""

    # AI Services
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
