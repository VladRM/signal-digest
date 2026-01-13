"""Application settings model."""
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class AppSettings(Base):
    """Persisted application settings."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    settings_json = Column(JSONB, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
