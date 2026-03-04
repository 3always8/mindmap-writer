from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from mindmap_writer.config import AppConfig, ModelConfig

# Fallback model configs when a provider's API key is missing
_GOOGLE_FALLBACK = ModelConfig(provider="google", model="gemini-2.0-flash-latest")
_ANTHROPIC_FALLBACK = ModelConfig(provider="anthropic", model="claude-sonnet-4-20250514")


def _resolve_config(model_config: ModelConfig, config: AppConfig) -> ModelConfig:
    """If the configured provider has no API key, fall back to the other provider."""
    if model_config.provider == "anthropic" and not config.settings.anthropic_api_key:
        if config.settings.google_api_key:
            return _GOOGLE_FALLBACK.model_copy(
                update={"temperature": model_config.temperature, "max_tokens": model_config.max_tokens}
            )
        raise ValueError("No API keys configured. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY in .env")
    if model_config.provider == "google" and not config.settings.google_api_key:
        if config.settings.anthropic_api_key:
            return _ANTHROPIC_FALLBACK.model_copy(
                update={"temperature": model_config.temperature, "max_tokens": model_config.max_tokens}
            )
        raise ValueError("No API keys configured. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY in .env")
    return model_config


def create_llm(model_config: ModelConfig, config: AppConfig):
    resolved = _resolve_config(model_config, config)
    if resolved.provider == "anthropic":
        return ChatAnthropic(
            model=resolved.model,
            api_key=config.settings.anthropic_api_key,
            temperature=resolved.temperature,
            max_tokens=resolved.max_tokens,
        )
    elif resolved.provider == "google":
        return ChatGoogleGenerativeAI(
            model=resolved.model,
            google_api_key=config.settings.google_api_key,
            temperature=resolved.temperature,
            max_output_tokens=resolved.max_tokens,
        )
    else:
        raise ValueError(f"Unknown provider: {resolved.provider}")


def create_vision_llm(config: AppConfig):
    return create_llm(config.vision_model, config)


def create_text_llm(config: AppConfig):
    return create_llm(config.text_model, config)
