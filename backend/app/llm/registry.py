"""Provider registry for dynamic provider management."""

import logging
from typing import Dict, Type

from .exceptions import ProviderNotFoundError
from .providers.base import ModelProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for model providers.

    Allows dynamic registration and retrieval of provider implementations.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._providers: Dict[str, Type[ModelProvider]] = {}

    def register(self, provider_class: Type[ModelProvider]) -> None:
        """Register a provider class.

        Args:
            provider_class: Provider class to register

        Example:
            >>> registry = ProviderRegistry()
            >>> registry.register(OpenAIProvider)
        """
        # Instantiate to get the name
        provider = provider_class()
        self._providers[provider.name] = provider_class
        logger.debug(f"Registered provider: {provider.name}")

    def get(self, name: str) -> Type[ModelProvider]:
        """Get a provider class by name.

        Args:
            name: Provider name (e.g., 'openai', 'anthropic')

        Returns:
            Provider class

        Raises:
            ProviderNotFoundError: If provider not found
        """
        if name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ProviderNotFoundError(
                f"Provider '{name}' not found. Available providers: {available}"
            )
        return self._providers[name]

    def list_providers(self) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())


# Global registry instance
_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get the global provider registry.

    Returns:
        Global ProviderRegistry instance
    """
    return _registry
