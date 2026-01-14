"""Reusable LLM model selection and factory module.

This module provides a flexible, provider-agnostic interface for creating
and managing LLM models across different providers (OpenAI, Anthropic, etc.).

Key features:
- Runtime model switching
- Provider registry pattern
- Optional model caching
- Type-safe configuration
- Zero application-specific dependencies (fully reusable)
"""

from .config import ModelConfig, ProviderCredentials
from .factory import CachedModelFactory, ModelFactory
from .registry import ProviderRegistry, get_registry

# Auto-register all providers
from .providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
    OpenRouterProvider,
)

_registry = get_registry()
_registry.register(OpenAIProvider)
_registry.register(AnthropicProvider)
_registry.register(GeminiProvider)
_registry.register(OpenRouterProvider)

__all__ = [
    "ModelConfig",
    "ProviderCredentials",
    "ModelFactory",
    "CachedModelFactory",
    "ProviderRegistry",
    "get_registry",
]
