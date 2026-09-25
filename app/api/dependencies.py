from functools import lru_cache

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.providers.base import ModelProvider
from app.providers.mock_provider import MockProvider


def get_model_provider(
    settings: Settings = Depends(get_settings),
) -> ModelProvider:
    """
    FastAPI dependency that returns the correct ModelProvider implementation.

    In development/testing: returns MockProvider (no API key needed).
    In production:          returns OpenAIProvider (reads key from settings).

    The endpoint never imports MockProvider or OpenAIProvider directly.
    It declares `provider: ModelProvider = Depends(get_model_provider)` and
    receives whichever implementation this function returns.

    Switching from OpenAI to Anthropic means changing one line here —
    nothing in any endpoint, agent, or service changes.
    """
    if settings.environment == "testing":
        return MockProvider()

    # Session 10: replace this with OpenAIProvider(settings.openai_api_key)
    # For now, mock provider is used in all environments.
    return MockProvider()
