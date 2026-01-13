"""Content item model."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.endpoint import ConnectorType


class ContentItem(Base):
    """Normalized content item from any connector."""

    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=True)
    connector_query_id = Column(
        Integer, ForeignKey("connector_queries.id"), nullable=True
    )
    connector_type = Column(Enum(ConnectorType), nullable=False)
    external_id = Column(String(512), nullable=True, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_text = Column(Text, nullable=True)
    raw_json = Column(JSONB, nullable=True)
    lang = Column(String(10), nullable=True)
    hash = Column(String(64), nullable=True, index=True)

    # Relationships
    endpoint = relationship("Endpoint")
    connector_query = relationship(
        "ConnectorQuery", back_populates="content_items"
    )
    topic_assignments = relationship("TopicAssignment", back_populates="content_item")
    ai_extractions = relationship("AIExtraction", back_populates="content_item")
