"""Run schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.run import RunType, RunStatus


class RunCreate(BaseModel):
    """Schema for creating a run."""

    run_type: RunType


class TavilyRunOptions(BaseModel):
    """Per-run Tavily search options."""

    enabled: bool | None = None
    search_depth: str | None = "advanced"
    max_results: int | None = 20
    topic: str | None = "news"
    time_range: str | None = "day"
    start_date: str | None = None
    end_date: str | None = None
    include_raw_content: bool | None = True
    include_answer: bool | None = None
    fetch_window_hours: int | None = None


class RunIngestionOptions(BaseModel):
    """Per-run ingestion options."""

    rss_max_items: int | None = None
    youtube_max_items: int | None = None
    twitter_max_items: int | None = None
    tavily: TavilyRunOptions | None = None


class RunAiOptions(BaseModel):
    """Per-run AI options."""

    timeout_seconds: int | None = None


class RunBriefOptions(BaseModel):
    """Per-run brief options."""

    max_items: int | None = None
    max_per_topic: int | None = None
    lookback_hours: int | None = None


class Run(BaseModel):
    """Schema for run response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_type: RunType
    started_at: datetime
    finished_at: datetime | None
    status: RunStatus
    stats_json: dict | None
    error_text: str | None
