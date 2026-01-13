"""Brief schemas."""
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from app.models.brief import BriefMode


class Brief(BaseModel):
    """Schema for brief response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    mode: BriefMode
    created_at: datetime


class BriefItemDetail(BaseModel):
    """Schema for brief item with full details."""

    model_config = ConfigDict(from_attributes=True)

    rank: int
    reason_included: str | None
    content_item: dict  # Will include full content item with extractions


class BriefWithItems(Brief):
    """Schema for brief with all items."""

    items: list[dict]  # Will be populated with BriefItemDetail
