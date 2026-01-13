"""Brief item model."""
from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class BriefItem(Base):
    """Item included in a brief."""

    __tablename__ = "brief_items"

    id = Column(Integer, primary_key=True, index=True)
    brief_id = Column(Integer, ForeignKey("briefs.id"), nullable=False)
    content_item_id = Column(Integer, ForeignKey("content_items.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    reason_included = Column(Text, nullable=True)

    # Relationships
    brief = relationship("Brief", back_populates="items")
    content_item = relationship("ContentItem")
