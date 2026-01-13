"""Topic assignment model."""
from sqlalchemy import Column, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TopicAssignment(Base):
    """Multi-label topic classification result."""

    __tablename__ = "topic_assignments"

    id = Column(Integer, primary_key=True, index=True)
    content_item_id = Column(Integer, ForeignKey("content_items.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    score = Column(Float, nullable=False)
    rationale_short = Column(Text, nullable=True)

    # Relationships
    content_item = relationship("ContentItem", back_populates="topic_assignments")
    topic = relationship("Topic")
