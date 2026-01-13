"""AI extraction model."""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class AIExtraction(Base):
    """Structured AI extraction result."""

    __tablename__ = "ai_extractions"

    id = Column(Integer, primary_key=True, index=True)
    content_item_id = Column(Integer, ForeignKey("content_items.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    prompt_name = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    extracted_json = Column(JSONB, nullable=False)
    quality_score = Column(Float, nullable=True)

    # Relationships
    content_item = relationship("ContentItem", back_populates="ai_extractions")
