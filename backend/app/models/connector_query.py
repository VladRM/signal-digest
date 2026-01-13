"""Connector query model."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.endpoint import ConnectorType


class ConnectorQuery(Base):
    """Generated connector query (e.g., Tavily query per topic)."""

    __tablename__ = "connector_queries"

    id = Column(Integer, primary_key=True, index=True)
    connector_type = Column(Enum(ConnectorType), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    query = Column(Text, nullable=False)
    options_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    topic = relationship("Topic")
    content_items = relationship("ContentItem", back_populates="connector_query")
