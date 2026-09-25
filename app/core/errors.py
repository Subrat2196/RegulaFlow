class RegulaFlowError(Exception):
    """
    Base class for all application-specific errors.

    Every custom exception in this codebase inherits from this.
    That means a single `except RegulaFlowError` in the FastAPI
    error handler will catch any internal error without catching
    unrelated Python errors (like KeyError or ValueError).
    """

    def __init__(self, message: str, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, context={self.context!r})"


class ProviderError(RegulaFlowError):
    """
    Raised when an LLM provider call fails for any reason.

    This is the parent for all provider-specific errors below.
    Catching ProviderError catches all of them.
    """


class RateLimitError(ProviderError):
    """
    Raised when the provider responds with HTTP 429 (Too Many Requests).

    This is always retryable — the provider is telling us to slow down,
    not that our request is wrong. Retry with exponential backoff.
    """


class ProviderTimeoutError(ProviderError):
    """
    Raised when a provider call exceeds the configured timeout.

    Named ProviderTimeoutError to avoid shadowing Python's built-in
    TimeoutError. Also retryable — a timeout is usually transient.
    """


class MalformedOutputError(ProviderError):
    """
    Raised when the provider returns text that cannot be parsed as
    the expected Pydantic schema.

    Example: structured_generate() asks for JSON matching
    RegulationRequirement, but the model outputs a markdown paragraph.

    This is retryable a limited number of times — the model might
    produce valid JSON on the next attempt with the same prompt.
    After max retries, it becomes RetryExhaustedError.
    """


class RetryExhaustedError(RegulaFlowError):
    """
    Raised when all retry attempts have been exhausted.

    Wraps the last underlying exception so callers know what the
    final failure was. The `attempts` field records how many times
    we tried before giving up — useful for structured logging.
    """

    def __init__(self, message: str, attempts: int, last_error: Exception) -> None:
        super().__init__(message, context={"attempts": attempts, "last_error": str(last_error)})
        self.attempts = attempts
        self.last_error = last_error


class ConfigurationError(RegulaFlowError):
    """
    Raised at startup when required configuration is missing or invalid.

    Unlike the errors above, this is NOT retryable. If the OpenAI API key
    is missing, retrying the same request 3 times won't fix it.
    The service should refuse to start, not silently fail mid-request.
    """
