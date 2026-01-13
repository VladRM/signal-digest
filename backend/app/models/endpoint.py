"""Endpoint model."""
from sqlalchemy import Boolean, Column, Enum, Integer, String, Text
import enum

from app.database import Base


class ConnectorType(str, enum.Enum):
    """Connector type enumeration."""

    RSS = "rss"
    YOUTUBE_CHANNEL = "youtube_channel"
    X_USER = "x_user"
    TAVILY = "tavily"


class Endpoint(Base):
    """Configured endpoint for a connector (RSS feed, YouTube channel, X handle)."""

    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    connector_type = Column(Enum(ConnectorType), nullable=False)
    name = Column(String(255), nullable=False)
    target = Column(Text, nullable=False)  # RSS URL, YouTube channel ID/URL, X handle
    enabled = Column(Boolean, default=True, nullable=False)
    weight = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)
