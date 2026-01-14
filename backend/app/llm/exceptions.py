"""Custom exceptions for LLM module."""


class LLMModuleError(Exception):
    """Base exception for LLM module errors."""

    pass


class ProviderNotFoundError(LLMModuleError):
    """Raised when a requested provider is not registered."""

    pass


class ModelCreationError(LLMModuleError):
    """Raised when model creation fails."""

    pass


class ConfigurationError(LLMModuleError):
    """Raised when configuration is invalid."""

    pass
