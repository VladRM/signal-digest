"""Google Gemini provider implementation."""

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from .base import ModelProvider

logger = logging.getLogger(__name__)


class GeminiProvider(ModelProvider):
    """Google Gemini provider implementation.

    Supports Google's Gemini models. Does not support reasoning effort.
    """

    @property
    def name(self) -> str:
        """Provider identifier."""
        return "gemini"

    def supports_reasoning_effort(self) -> bool:
        """Gemini does not support reasoning effort."""
        return False

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate Gemini-specific configuration.

        Args:
            config: Configuration dictionary
        """
        # Check for api_key or google_api_key
        if not config.get("api_key"):
            logger.warning("Google API key not provided")

        # Warn if reasoning_effort specified
        if config.get("reasoning_effort") and config.get("reasoning_effort") != "none":
            logger.warning(
                "Gemini does not support reasoning_effort parameter, will be ignored"
            )

    def create_model(
        self,
        model: str,
        temperature: float,
        reasoning_effort: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create Gemini ChatModel instance.

        Args:
            model: Model name (e.g., 'gemini-pro')
            temperature: Sampling temperature
            reasoning_effort: Ignored for Gemini
            **kwargs: Additional arguments (google_api_key, etc.)

        Returns:
            Configured ChatGoogleGenerativeAI instance
        """
        # Remove model_kwargs if present
        kwargs.pop("model_kwargs", None)

        # Rename api_key to google_api_key if present
        if "api_key" in kwargs:
            kwargs["google_api_key"] = kwargs.pop("api_key")

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            **kwargs,
        )
