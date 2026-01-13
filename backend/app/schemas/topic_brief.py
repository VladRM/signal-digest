"""Topic brief schemas."""

from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime


class ContentReference(BaseModel):
    """Content reference in topic brief."""
    content_item_id: int
    title: str
    url: str
    key_point: str


class TopicBrief(BaseModel):
    """Topic brief response schema."""
    id: int
    topic_id: int
    topic_name: str
    summary_short: str
    summary_full: str
    content_references: List[ContentReference]
    key_themes: List[str]
    significance: str
    created_at: datetime

    class Config:
        from_attributes = True
