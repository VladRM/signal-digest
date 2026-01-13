"""Content item schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ContentItem(BaseModel):
    """Schema for content item response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    endpoint_id: int | None
    connector_query_id: int | None
    connector_type: str
    external_id: str | None
    url: str
    title: str
    author: str | None
    published_at: datetime | None
    fetched_at: datetime
    raw_text: str | None
    lang: str | None
    hash: str | None
