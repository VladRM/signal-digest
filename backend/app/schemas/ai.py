"""Schemas for AI-related API responses."""

from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.topic_brief import TopicBrief


class TopicAssignmentSchema(BaseModel):
    """Schema for topic assignment."""
    topic_id: int
    topic_name: str
    score: float
    rationale_short: str

    class Config:
        from_attributes = True


class EndpointSchema(BaseModel):
    """Schema for endpoint information."""

    id: int
    name: str
    connector_type: str
    target: str

    class Config:
        from_attributes = True


class ConnectorQuerySchema(BaseModel):
    """Schema for connector query information."""

    id: int
    connector_type: str
    query: str
    topic_id: Optional[int] = None
    topic_name: Optional[str] = None

    class Config:
        from_attributes = True


class AIExtractionSchema(BaseModel):
    """Schema for AI extraction."""
    summary_bullets: List[str]
    why_it_matters: List[str]
    key_claims: List[dict]
    novelty: str
    confidence_overall: str
    follow_ups: Optional[List[str]] = None


class ContentItemWithDetails(BaseModel):
    """Full content item with all related data."""
    id: int
    title: str
    url: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    raw_text: Optional[str] = None
    connector_type: str
    endpoint: Optional[EndpointSchema] = None
    connector_query: Optional[ConnectorQuerySchema] = None
    extraction: AIExtractionSchema
    topics: List[TopicAssignmentSchema]

    class Config:
        from_attributes = True


class BriefItemDetail(BaseModel):
    """Brief item with content details."""
    rank: int
    reason_included: str
    content_item: ContentItemWithDetails

    class Config:
        from_attributes = True


class BriefWithItems(BaseModel):
    """Brief with all items."""
    id: int
    date: date
    mode: str
    created_at: datetime
    items: List[BriefItemDetail]
    topic_briefs: Optional[List[TopicBrief]] = []

    class Config:
        from_attributes = True
