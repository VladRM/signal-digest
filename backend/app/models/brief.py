"""Brief model."""
from sqlalchemy import Column, Date, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class BriefMode(str, enum.Enum):
    """Brief mode enumeration."""

    MORNING = "morning"


class Brief(Base):
    """Daily brief."""

    __tablename__ = "briefs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    mode = Column(Enum(BriefMode), default=BriefMode.MORNING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    items = relationship("BriefItem", back_populates="brief", order_by="BriefItem.rank")
    topic_briefs = relationship("TopicBrief", back_populates="brief")
