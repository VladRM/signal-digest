"""OpenRouter provider implementation."""

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .base import ModelProvider

logger = logging.getLogger(__name__)


class OpenRouterProvider(ModelProvider):
    """OpenRouter provider implementation.

    OpenRouter is an OpenAI-compatible API that provides access to multiple
    models. Supports reasoning effort for compatible models.
    """

    @property
    def name(self) -> str:
        """Provider identifier."""
        return "openrouter"

    def supports_reasoning_effort(self) -> bool:
        """OpenRouter supports reasoning effort (OpenAI-compatible)."""
        return True

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate OpenRouter-specific configuration.

        Args:
            config: Configuration dictionary
        """
        if not config.get("api_key"):
            logger.warning("OpenRouter API key not provided")

        if not config.get("base_url"):
            logger.warning(
                "OpenRouter base_url not provided, defaulting to https://openrouter.ai/api/v1"
            )

    def create_model(
        self,
        model: str,
        temperature: float,
        reasoning_effort: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create OpenRouter ChatModel instance.

        Args:
            model: Model name (e.g., 'anthropic/claude-3-opus')
            temperature: Sampling temperature
            reasoning_effort: Optional reasoning effort level
            **kwargs: Additional arguments (api_key, base_url, extra_headers, etc.)

        Returns:
            Configured ChatOpenAI instance (OpenRouter is OpenAI-compatible)
        """
        # Ensure base_url is set
        if "base_url" not in kwargs:
            kwargs["base_url"] = "https://openrouter.ai/api/v1"

        # Handle OpenRouter-specific headers
        openrouter_headers = kwargs.pop("extra_headers", {})

        # Handle reasoning effort
        openai_kwargs = {}
        if reasoning_effort and reasoning_effort != "none":
            openai_kwargs["model_kwargs"] = {"reasoning_effort": reasoning_effort}
            logger.debug(f"Setting reasoning_effort={reasoning_effort} for OpenRouter")

        # Merge with any extra model_kwargs
        if "model_kwargs" in kwargs:
            openai_kwargs.setdefault("model_kwargs", {}).update(
                kwargs.pop("model_kwargs")
            )

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            default_headers=openrouter_headers or None,
            **openai_kwargs,
            **kwargs,
        )
