import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_are_correct():
    """All defaults should load without any environment variables set."""
    settings = Settings()

    assert settings.app_name == "RegulaFlow"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"


def test_environment_variable_overrides_default(monkeypatch):
    """
    An environment variable should override the default value.

    monkeypatch is a pytest fixture that temporarily sets environment variables
    for the duration of one test, then restores the original state. This keeps
    tests isolated from each other.
    """
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings()

    assert settings.log_level == "DEBUG"
    assert settings.debug is True


def test_invalid_environment_is_rejected(monkeypatch):
    """
    An invalid ENVIRONMENT value should raise a ValidationError.
    The app should refuse to start rather than run with bad config.
    """
    monkeypatch.setenv("ENVIRONMENT", "staging")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "environment" in str(exc_info.value).lower()


def test_invalid_log_level_is_rejected(monkeypatch):
    """Only DEBUG, INFO, WARNING, ERROR, CRITICAL are valid log levels."""
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")

    with pytest.raises(ValidationError):
        Settings()


def test_unknown_env_vars_are_ignored(monkeypatch):
    """
    Extra environment variables (not defined in Settings) should be silently
    ignored, not cause a crash. This comes from extra="ignore" in model_config.
    """
    monkeypatch.setenv("SOME_RANDOM_VARIABLE_WE_NEVER_DEFINED", "hello")

    settings = Settings()

    assert settings.app_name == "RegulaFlow"


def test_case_insensitive_env_var(monkeypatch):
    """
    Environment variable names should be case-insensitive.
    LOG_LEVEL, log_level, and Log_Level should all work.
    """
    monkeypatch.setenv("log_level", "WARNING")

    settings = Settings()

    assert settings.log_level == "WARNING"
