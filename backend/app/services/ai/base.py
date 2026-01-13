"""Base class for AI services."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.services.ai.constants import MODEL_NAME, TEMPERATURE, MAX_RETRIES


class BaseAIService(ABC):
    """Base class for all AI services using LangGraph."""

    def __init__(self, db: Session):
        """Initialize the AI service.

        Args:
            db: Database session
        """
        self.db = db
        self.llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=settings.google_api_key,
            temperature=TEMPERATURE,
            max_retries=MAX_RETRIES,
        )
        self.stats = {
            "items_processed": 0,
            "items_succeeded": 0,
            "items_failed": 0,
            "errors": [],
        }

    @abstractmethod
    async def process(self, content_item) -> Dict[str, Any]:
        """Process a single content item.

        Args:
            content_item: ContentItem to process

        Returns:
            Dict with processing results
        """
        pass

    def update_stats(self, success: bool, error: Optional[str] = None):
        """Update processing statistics.

        Args:
            success: Whether processing succeeded
            error: Error message if failed
        """
        self.stats["items_processed"] += 1
        if success:
            self.stats["items_succeeded"] += 1
        else:
            self.stats["items_failed"] += 1
            if error:
                self.stats["errors"].append(error)

    def get_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics to zero."""
        self.stats = {
            "items_processed": 0,
            "items_succeeded": 0,
            "items_failed": 0,
            "errors": [],
        }

    def _llm_with_timeout(self, timeout_seconds: float | None):
        if timeout_seconds is None:
            return self.llm
        return self.llm.bind(timeout=float(timeout_seconds))
