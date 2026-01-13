"""Topic brief model."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class TopicBrief(Base):
    """AI-generated executive summary for a topic within a brief."""

    __tablename__ = "topic_briefs"

    id = Column(Integer, primary_key=True, index=True)
    brief_id = Column(Integer, ForeignKey("briefs.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)

    # Short summary for collapsed state (2-3 sentences)
    summary_short = Column(Text, nullable=False)

    # Full executive summary with details
    summary_full = Column(Text, nullable=False)

    # Array of content item IDs used in this brief
    content_item_ids = Column(ARRAY(Integer), nullable=False)

    # JSONB for structured content references
    content_references = Column(JSONB, nullable=False)

    # AI generation metadata
    model_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    brief = relationship("Brief", back_populates="topic_briefs")
    topic = relationship("Topic")
