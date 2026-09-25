import asyncio
import functools
import random
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from app.core.errors import RetryExhaustedError
from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])

# The exception types that are safe to retry.
# Imported lazily to avoid a circular import in tests.
_DEFAULT_RETRYABLE = ()


def _default_retryable_exceptions() -> tuple[type[Exception], ...]:
    from app.core.errors import MalformedOutputError, ProviderTimeoutError, RateLimitError

    return (RateLimitError, ProviderTimeoutError, MalformedOutputError)


def retry_with_backoff(
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[F], F]:
    """
    Decorator that retries an async function with exponential backoff.

    How it works:
        Attempt 1: call the function.
        If it raises a retryable exception:
            Wait base_delay * (2 ** attempt) seconds, capped at max_delay.
            Add optional random jitter to prevent thundering herd.
        Attempt 2: call again.
        ... repeat up to max_attempts.
        After all attempts fail: raise RetryExhaustedError.

    Args:
        max_attempts:  Total number of tries (including the first one).
        base_delay:    Starting delay in seconds (doubles each retry).
        max_delay:     Upper cap on delay — prevents infinite waits.
        jitter:        Add random noise to delays so 100 clients
                       don't all retry at the exact same millisecond.
        retryable_exceptions: Which exception types trigger a retry.
                       Defaults to (RateLimitError, ProviderTimeoutError,
                       MalformedOutputError). Any other exception propagates
                       immediately without retrying.

    Usage:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        async def call_openai(prompt: str) -> ModelResponse:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            exceptions = retryable_exceptions or _default_retryable_exceptions()
            last_error: Exception | None = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    is_last_attempt = attempt == max_attempts - 1

                    if is_last_attempt:
                        break

                    delay = min(base_delay * (2**attempt), max_delay)
                    if jitter:
                        delay *= 0.5 + random.random() * 0.5  # scale between 50%–100% of computed delay

                    logger.warning(
                        "provider_retry",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay_seconds=round(delay, 3),
                        error=str(exc),
                        error_type=type(exc).__name__,
                        function=func.__name__,
                    )
                    await asyncio.sleep(delay)

            raise RetryExhaustedError(
                message=f"{func.__name__} failed after {max_attempts} attempts",
                attempts=max_attempts,
                last_error=last_error,  # type: ignore[arg-type]
            )

        return wrapper  # type: ignore[return-value]

    return decorator
