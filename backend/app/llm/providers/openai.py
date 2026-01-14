"""OpenAI provider implementation."""

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .base import ModelProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(ModelProvider):
    """OpenAI provider implementation.

    Supports standard OpenAI API and reasoning effort parameter.
    """

    @property
    def name(self) -> str:
        """Provider identifier."""
        return "openai"

    def supports_reasoning_effort(self) -> bool:
        """OpenAI supports reasoning effort."""
        return True

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate OpenAI-specific configuration.

        Args:
            config: Configuration dictionary
        """
        if not config.get("api_key"):
            logger.warning("OpenAI API key not provided")

    def create_model(
        self,
        model: str,
        temperature: float,
        reasoning_effort: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create OpenAI ChatModel instance.

        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-5.1')
            temperature: Sampling temperature
            reasoning_effort: Optional reasoning effort level
            **kwargs: Additional arguments (api_key, base_url, etc.)

        Returns:
            Configured ChatOpenAI instance
        """
        # Handle reasoning effort
        openai_kwargs = {}
        if reasoning_effort and reasoning_effort != "none":
            openai_kwargs["model_kwargs"] = {"reasoning_effort": reasoning_effort}
            logger.debug(f"Setting reasoning_effort={reasoning_effort} for OpenAI")

        # Merge with any extra model_kwargs
        if "model_kwargs" in kwargs:
            openai_kwargs.setdefault("model_kwargs", {}).update(
                kwargs.pop("model_kwargs")
            )

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            **openai_kwargs,
            **kwargs,
        )
