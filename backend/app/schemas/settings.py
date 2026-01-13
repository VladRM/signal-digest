"""Settings schemas."""
from typing import Literal
from pydantic import BaseModel, Field


class IngestionSettings(BaseModel):
    """Ingestion settings stored in the database."""

    rss_max_items: int = 10
    youtube_max_items: int = 2
    twitter_max_items: int = 5


class TavilySettings(BaseModel):
    """Tavily settings stored in the database."""

    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "advanced"
    max_results: int = 20
    topic: Literal["general", "news", "finance"] = "news"
    time_range: Literal["none", "day", "week", "month", "year"] = "day"
    include_raw_content: bool = True


class AiSettings(BaseModel):
    """AI settings stored in the database."""

    timeout_seconds: int = 900
    classification_timeout_seconds: int = 60
    extraction_timeout_seconds: int = 90


class BriefSettings(BaseModel):
    """Brief settings stored in the database."""

    max_items: int = 15
    max_per_topic: int = 3
    lookback_hours: int = 48
    topic_brief_timeout_seconds: int = 60
    topic_brief_batch_size: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Number of items per batch for topic brief generation"
    )


class AppSettings(BaseModel):
    """Top-level application settings."""

    ingestion: IngestionSettings = IngestionSettings()
    tavily: TavilySettings = TavilySettings()
    ai: AiSettings = AiSettings()
    brief: BriefSettings = BriefSettings()
