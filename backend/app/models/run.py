"""Run model."""
from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.database import Base


class RunType(str, enum.Enum):
    """Run type enumeration."""

    INGEST = "ingest"
    AI = "ai"
    BUILD_BRIEF = "build_brief"


class RunStatus(str, enum.Enum):
    """Run status enumeration."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Run(Base):
    """Execution log for ingestion, AI processing, or brief building."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    run_type = Column(Enum(RunType), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(Enum(RunStatus), default=RunStatus.RUNNING, nullable=False)
    stats_json = Column(JSONB, nullable=True)
    error_text = Column(Text, nullable=True)
