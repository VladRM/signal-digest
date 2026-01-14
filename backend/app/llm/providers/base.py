"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel


class ModelProvider(ABC):
    """Abstract base class for LLM providers.

    Each provider implementation must:
    1. Specify a unique provider name
    2. Declare which features it supports
    3. Implement model creation logic
    4. Validate provider-specific configuration
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'openai', 'anthropic')."""
        pass

    @abstractmethod
    def supports_reasoning_effort(self) -> bool:
        """Whether this provider supports reasoning effort parameter."""
        pass

    @abstractmethod
    def create_model(
        self,
        model: str,
        temperature: float,
        reasoning_effort: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create and configure the model instance.

        Args:
            model: Model name/identifier
            temperature: Sampling temperature
            reasoning_effort: Optional reasoning effort level
            **kwargs: Provider-specific additional arguments

        Returns:
            Configured BaseChatModel instance

        Raises:
            ModelCreationError: If model creation fails
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate provider-specific configuration.

        Args:
            config: Configuration dictionary

        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass
