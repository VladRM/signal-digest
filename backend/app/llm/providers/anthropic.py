"""Anthropic provider implementation."""

import logging
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from .base import ModelProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(ModelProvider):
    """Anthropic provider implementation.

    Supports Claude models. Does not support reasoning effort.
    """

    @property
    def name(self) -> str:
        """Provider identifier."""
        return "anthropic"

    def supports_reasoning_effort(self) -> bool:
        """Anthropic does not support reasoning effort."""
        return False

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate Anthropic-specific configuration.

        Args:
            config: Configuration dictionary
        """
        if not config.get("api_key"):
            logger.warning("Anthropic API key not provided")

        # Warn if reasoning_effort specified (validation also happens in ModelConfig)
        if config.get("reasoning_effort") and config.get("reasoning_effort") != "none":
            logger.warning(
                "Anthropic does not support reasoning_effort parameter, will be ignored"
            )

    def create_model(
        self,
        model: str,
        temperature: float,
        reasoning_effort: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create Anthropic ChatModel instance.

        Args:
            model: Model name (e.g., 'claude-3-opus-20240229')
            temperature: Sampling temperature
            reasoning_effort: Ignored for Anthropic
            **kwargs: Additional arguments (api_key, etc.)

        Returns:
            Configured ChatAnthropic instance
        """
        # Remove model_kwargs if present (not applicable to Anthropic)
        kwargs.pop("model_kwargs", None)

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            **kwargs,
        )
