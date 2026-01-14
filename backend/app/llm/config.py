"""Configuration schemas for LLM models."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    """Runtime model configuration.

    This configuration is immutable (frozen) for thread safety when used
    across concurrent requests.

    Attributes:
        provider: LLM provider identifier
        model: Model name/identifier
        temperature: Sampling temperature (0.0-2.0)
        reasoning_effort: Reasoning effort level (OpenAI-specific)
        api_key: Optional provider API key override
        base_url: Optional base URL override (for OpenRouter, custom endpoints)
        extra_headers: Optional extra HTTP headers
        model_kwargs: Optional provider-specific kwargs
    """

    provider: Literal["openai", "anthropic", "gemini", "openrouter"]
    model: str
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    reasoning_effort: Literal["none", "low", "medium", "high"] = "none"

    # Provider-specific configurations
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    extra_headers: Optional[Dict[str, str]] = None
    model_kwargs: Optional[Dict[str, Any]] = None

    model_config = {"frozen": True}  # Immutable for thread safety

    @field_validator("reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, v: str, info) -> str:
        """Validate reasoning effort and log warnings for unsupported providers."""
        if v != "none":
            provider = info.data.get("provider")
            if provider in ["anthropic", "gemini"]:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"reasoning_effort='{v}' not supported by {provider}, will be ignored"
                )
        return v


class ProviderCredentials(BaseModel):
    """Provider credentials configuration.

    Separate from ModelConfig for security - credentials should not be
    serialized or logged with model configurations.

    Attributes:
        openai_api_key: OpenAI API key
        anthropic_api_key: Anthropic API key
        google_api_key: Google AI Studio API key
        openrouter_api_key: OpenRouter API key
        openrouter_base_url: OpenRouter base URL
        openrouter_app_url: OpenRouter app URL (for HTTP-Referer header)
        openrouter_app_name: OpenRouter app name (for X-Title header)
    """

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_url: Optional[str] = None
    openrouter_app_name: Optional[str] = None
