import pytest

from app.core.errors import (
    ConfigurationError,
    MalformedOutputError,
    ProviderTimeoutError,
    RateLimitError,
    RetryExhaustedError,
)
from app.core.retry import retry_with_backoff


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

def test_rate_limit_is_a_provider_error():
    from app.core.errors import ProviderError

    exc = RateLimitError("429 Too Many Requests")
    assert isinstance(exc, ProviderError)


def test_retry_exhausted_stores_attempts_and_last_error():
    cause = RateLimitError("hit limit")
    exc = RetryExhaustedError("gave up", attempts=3, last_error=cause)

    assert exc.attempts == 3
    assert exc.last_error is cause
    assert "3" in exc.context["attempts"].__str__()


def test_configuration_error_is_not_provider_error():
    from app.core.errors import ProviderError

    exc = ConfigurationError("missing API key")
    assert not isinstance(exc, ProviderError)


# ---------------------------------------------------------------------------
# retry_with_backoff — basic success
# ---------------------------------------------------------------------------

async def test_succeeds_on_first_attempt():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.0)
    async def always_succeeds() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await always_succeeds()
    assert result == "ok"
    assert call_count == 1


# ---------------------------------------------------------------------------
# retry_with_backoff — retry on retryable exceptions
# ---------------------------------------------------------------------------

async def test_retries_on_rate_limit_error(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.0, jitter=False)
    async def fails_twice_then_succeeds() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError("429")
        return "success"

    result = await fails_twice_then_succeeds()
    assert result == "success"
    assert call_count == 3


async def test_retries_on_malformed_output(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    call_count = 0

    @retry_with_backoff(max_attempts=2, base_delay=0.0, jitter=False)
    async def bad_json_once() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise MalformedOutputError("expected JSON, got markdown")
        return "fixed"

    result = await bad_json_once()
    assert result == "fixed"
    assert call_count == 2


async def test_retries_on_timeout(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    call_count = 0

    @retry_with_backoff(max_attempts=2, base_delay=0.0, jitter=False)
    async def times_out_once() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ProviderTimeoutError("timed out after 30s")
        return "recovered"

    result = await times_out_once()
    assert result == "recovered"


# ---------------------------------------------------------------------------
# retry_with_backoff — exhaustion
# ---------------------------------------------------------------------------

async def test_raises_retry_exhausted_after_all_attempts(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _no_sleep)

    @retry_with_backoff(max_attempts=3, base_delay=0.0, jitter=False)
    async def always_rate_limited() -> str:
        raise RateLimitError("429 forever")

    with pytest.raises(RetryExhaustedError) as exc_info:
        await always_rate_limited()

    error = exc_info.value
    assert error.attempts == 3
    assert isinstance(error.last_error, RateLimitError)


async def test_retry_exhausted_message_contains_function_name(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _no_sleep)

    @retry_with_backoff(max_attempts=2, base_delay=0.0, jitter=False)
    async def my_specific_function() -> str:
        raise RateLimitError("nope")

    with pytest.raises(RetryExhaustedError) as exc_info:
        await my_specific_function()

    assert "my_specific_function" in str(exc_info.value)


# ---------------------------------------------------------------------------
# retry_with_backoff — non-retryable exceptions propagate immediately
# ---------------------------------------------------------------------------

async def test_non_retryable_exception_propagates_without_retry():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.0, jitter=False)
    async def raises_value_error() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("bad input — do not retry this")

    with pytest.raises(ValueError, match="bad input"):
        await raises_value_error()

    assert call_count == 1  # called once, not 3 times


async def test_configuration_error_propagates_immediately():
    """ConfigurationError must never be retried — missing keys won't appear on retry."""
    call_count = 0

    @retry_with_backoff(max_attempts=5, base_delay=0.0)
    async def misconfigured() -> str:
        nonlocal call_count
        call_count += 1
        raise ConfigurationError("OPENAI_API_KEY is not set")

    with pytest.raises(ConfigurationError):
        await misconfigured()

    assert call_count == 1


# ---------------------------------------------------------------------------
# retry_with_backoff — custom retryable exception list
# ---------------------------------------------------------------------------

async def test_custom_retryable_exceptions(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    call_count = 0

    class MyTransientError(Exception):
        pass

    @retry_with_backoff(
        max_attempts=3,
        base_delay=0.0,
        jitter=False,
        retryable_exceptions=(MyTransientError,),
    )
    async def custom_retryable() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise MyTransientError("transient")
        return "done"

    result = await custom_retryable()
    assert result == "done"
    assert call_count == 3


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _no_sleep(_seconds: float) -> None:
    """Drop-in replacement for asyncio.sleep that returns immediately in tests."""
