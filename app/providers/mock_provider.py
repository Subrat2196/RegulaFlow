from collections.abc import AsyncIterator

from pydantic import BaseModel

from app.providers.base import ModelProvider, ModelResponse


class MockProvider(ModelProvider):
    """
    A fake LLM provider that returns configurable canned responses.

    Used everywhere the real provider would be in tests and local development.
    No API key, no network, no cost, no latency, fully deterministic.

    How it works:
        You configure response queues in the constructor.
        Each call pops from the front of the queue.
        When the queue is empty, a safe default is returned.
        The call_count attribute lets tests verify how many times the
        provider was called — useful for checking that agents aren't
        making unnecessary model calls.

    Example:
        provider = MockProvider(
            generate_responses=["Summary of GDPR Article 17."],
            structured_responses=['{"section": "4.2", "confidence": 0.93, ...}'],
        )
        response = await provider.generate("Summarize this regulation.")
        assert response.content == "Summary of GDPR Article 17."
    """

    DEFAULT_TEXT = "This is a mock text response generated for testing."
    DEFAULT_JSON = '{"result": "mock_value"}'

    def __init__(
        self,
        generate_responses: list[str] | None = None,
        structured_responses: list[str] | None = None,
    ) -> None:
        # Queues are lists used as FIFO (first in, first out) structures.
        # pop(0) takes from the front; append() adds to the back.
        self._generate_queue: list[str] = list(generate_responses or [])
        self._structured_queue: list[str] = list(structured_responses or [])
        self.call_count: int = 0

    def _pop(self, queue: list[str], default: str) -> str:
        """Return the next queued response, or the default if the queue is empty."""
        return queue.pop(0) if queue else default

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        content = self._pop(self._generate_queue, self.DEFAULT_TEXT)
        self.call_count += 1
        return ModelResponse(
            content=content,
            model="mock",
            input_tokens=len(prompt.split()),
            output_tokens=len(content.split()),
            latency_ms=0.1,
        )

    async def structured_generate(
        self,
        prompt: str,
        response_schema: type[BaseModel],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        content = self._pop(self._structured_queue, self.DEFAULT_JSON)
        self.call_count += 1
        return ModelResponse(
            content=content,
            model="mock",
            input_tokens=len(prompt.split()),
            output_tokens=len(content.split()),
            latency_ms=0.1,
        )

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        content = self._pop(self._generate_queue, self.DEFAULT_TEXT)
        self.call_count += 1
        for word in content.split():
            yield word + " "
