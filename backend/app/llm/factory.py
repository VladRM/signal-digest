"""Model factory for creating LLM instances."""

import logging
from typing import Dict, Optional

from langchain_core.language_models import BaseChatModel

from .config import ModelConfig, ProviderCredentials
from .exceptions import ModelCreationError
from .registry import get_registry

logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory for creating LLM models with runtime configuration.

    This factory creates model instances based on ModelConfig, handling
    provider selection, credential injection, and configuration validation.
    """

    def __init__(self, credentials: Optional[ProviderCredentials] = None):
        """Initialize factory with credentials.

        Args:
            credentials: Provider credentials (if None, providers must supply their own)
        """
        self._credentials = credentials
        self._registry = get_registry()

    def create_model(self, config: ModelConfig) -> BaseChatModel:
        """Create a model instance from configuration.

        Args:
            config: Model configuration

        Returns:
            Configured BaseChatModel instance

        Raises:
            ModelCreationError: If model creation fails
        """
        try:
            # Get provider class
            provider_class = self._registry.get(config.provider)
            provider = provider_class()

            # Validate configuration
            provider.validate_config(config.model_dump())

            # Extract credentials for this provider
            api_key = self._get_api_key_for_provider(config.provider)

            # Prepare kwargs
            kwargs = {}
            if config.base_url:
                kwargs["base_url"] = config.base_url
            if config.extra_headers:
                kwargs["extra_headers"] = config.extra_headers
            if config.model_kwargs:
                kwargs.update(config.model_kwargs)
            if api_key:
                kwargs["api_key"] = api_key
            # Override with explicit api_key from config if provided
            if config.api_key:
                kwargs["api_key"] = config.api_key

            # Create model
            model = provider.create_model(
                model=config.model,
                temperature=config.temperature,
                reasoning_effort=(
                    config.reasoning_effort
                    if provider.supports_reasoning_effort()
                    else None
                ),
                **kwargs,
            )

            logger.info(f"Created {config.provider} model: {config.model}")
            return model

        except Exception as e:
            logger.error(f"Failed to create model: {e}")
            raise ModelCreationError(f"Model creation failed: {e}") from e

    def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Extract API key for specific provider from credentials.

        Args:
            provider: Provider name

        Returns:
            API key or None
        """
        if not self._credentials:
            return None

        key_mapping = {
            "openai": self._credentials.openai_api_key,
            "anthropic": self._credentials.anthropic_api_key,
            "gemini": self._credentials.google_api_key,
            "openrouter": self._credentials.openrouter_api_key,
        }
        return key_mapping.get(provider)


class CachedModelFactory(ModelFactory):
    """Model factory with caching for frequently used configurations.

    This factory caches model instances by their configuration signature,
    significantly improving performance for repeated requests with the same
    model configuration.
    """

    def __init__(self, credentials: Optional[ProviderCredentials] = None):
        """Initialize cached factory.

        Args:
            credentials: Provider credentials
        """
        super().__init__(credentials)
        self._cache: Dict[str, BaseChatModel] = {}

    def create_model(self, config: ModelConfig) -> BaseChatModel:
        """Create or retrieve cached model.

        Args:
            config: Model configuration

        Returns:
            Cached or newly created BaseChatModel instance
        """
        cache_key = self._make_cache_key(config)

        if cache_key not in self._cache:
            logger.debug(f"Cache miss for {cache_key}, creating new model")
            self._cache[cache_key] = super().create_model(config)
        else:
            logger.debug(f"Cache hit for {cache_key}, reusing model")

        return self._cache[cache_key]

    def _make_cache_key(self, config: ModelConfig) -> str:
        """Create cache key from config.

        Args:
            config: Model configuration

        Returns:
            Cache key string
        """
        return f"{config.provider}:{config.model}:{config.temperature}:{config.reasoning_effort}"

    def clear_cache(self) -> None:
        """Clear the model cache."""
        logger.info(f"Clearing model cache ({len(self._cache)} entries)")
        self._cache.clear()

    def cache_size(self) -> int:
        """Get current cache size.

        Returns:
            Number of cached models
        """
        return len(self._cache)
