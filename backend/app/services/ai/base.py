"""Base class for AI services."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.llm import CachedModelFactory, ModelConfig, ProviderCredentials


# Module-level factory instance for efficient model caching
_credentials = ProviderCredentials(
    google_api_key=settings.google_api_key,
    openai_api_key=settings.openai_api_key,
    anthropic_api_key=settings.anthropic_api_key,
    openrouter_api_key=settings.openrouter_api_key,
)
_factory = CachedModelFactory(_credentials)


def get_default_model_config() -> ModelConfig:
    """Get default model configuration from settings."""
    return ModelConfig(
        provider=settings.llm_provider,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )


class BaseAIService(ABC):
    """Base class for all AI services using LangGraph."""

    def __init__(self, db: Session):
        """Initialize the AI service.

        Args:
            db: Database session
        """
        self.db = db
        self.llm = _factory.create_model(get_default_model_config())
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
