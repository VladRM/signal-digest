"""Topic model."""
from sqlalchemy import Boolean, Column, Integer, String, Text

from app.database import Base


class Topic(Base):
    """Topic for content classification."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    include_rules = Column(Text, nullable=True)
    exclude_rules = Column(Text, nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
