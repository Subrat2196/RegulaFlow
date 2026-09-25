import pytest
from pydantic import BaseModel

from app.providers.base import ModelProvider, ModelResponse
from app.providers.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# Abstract base class contract
# ---------------------------------------------------------------------------

def test_model_provider_cannot_be_instantiated_directly():
    """
    ModelProvider is abstract — instantiating it directly must raise TypeError.
    This confirms the ABC contract is enforced by Python, not just documented.
    """
    with pytest.raises(TypeError):
        ModelProvider()  # type: ignore


def test_mock_provider_is_a_model_provider():
    """
    MockProvider must pass isinstance(provider, ModelProvider).
    This is the check FastAPI's dependency injection uses to verify
    the injected provider fulfills the contract.
    """
    provider = MockProvider()
    assert isinstance(provider, ModelProvider)


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------

async def test_generate_returns_model_response():
    """generate() must return a ModelResponse — the standardized type."""
    provider = MockProvider()
    response = await provider.generate("Summarize this regulation.")

    assert isinstance(response, ModelResponse)
    assert response.model == "mock"
    assert response.content == MockProvider.DEFAULT_TEXT


async def test_generate_returns_configured_responses_in_order():
    """
    Responses are returned in the order they were configured.
    When the queue is exhausted, the default is returned.
    """
    provider = MockProvider(generate_responses=["First response.", "Second response."])

    r1 = await provider.generate("prompt 1")
    r2 = await provider.generate("prompt 2")
    r3 = await provider.generate("prompt 3")  # queue empty — falls back to default

    assert r1.content == "First response."
    assert r2.content == "Second response."
    assert r3.content == MockProvider.DEFAULT_TEXT


async def test_call_count_tracks_generate_calls():
    provider = MockProvider()
    assert provider.call_count == 0

    await provider.generate("p1")
    await provider.generate("p2")
    await provider.generate("p3")

    assert provider.call_count == 3


async def test_generate_records_token_counts():
    """
    Token counts are approximated by word count in the mock.
    The real provider will use exact values from the API response.
    """
    provider = MockProvider()
    response = await provider.generate("This is a test prompt with seven words here.")

    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.latency_ms >= 0.0


# ---------------------------------------------------------------------------
# structured_generate()
# ---------------------------------------------------------------------------

async def test_structured_generate_returns_parseable_json():
    """
    The content of a structured_generate response must be valid JSON
    that can be parsed by the provided schema.
    """
    class RequirementExtraction(BaseModel):
        section: str
        requirement_text: str
        confidence: float

    provider = MockProvider(
        structured_responses=[
            '{"section": "4.2", "requirement_text": "Retain records for 5 years.", "confidence": 0.93}'
        ]
    )
    response = await provider.structured_generate(
        "Extract the requirement from section 4.2.",
        RequirementExtraction,
    )

    assert isinstance(response, ModelResponse)
    parsed = RequirementExtraction.model_validate_json(response.content)
    assert parsed.section == "4.2"
    assert parsed.confidence == 0.93


async def test_structured_generate_uses_its_own_queue():
    """
    structured_generate draws from _structured_queue, not _generate_queue.
    Calling generate() should not consume structured responses and vice versa.
    """
    provider = MockProvider(
        generate_responses=["Text response."],
        structured_responses=['{"result": "structured"}'],
    )
    text_response = await provider.generate("any prompt")
    struct_response = await provider.structured_generate("any prompt", BaseModel)

    assert text_response.content == "Text response."
    assert struct_response.content == '{"result": "structured"}'


async def test_call_count_includes_structured_generate():
    """call_count must count all model calls — generate and structured_generate."""
    provider = MockProvider()
    await provider.generate("p1")
    await provider.structured_generate("p2", BaseModel)
    await provider.structured_generate("p3", BaseModel)

    assert provider.call_count == 3


# ---------------------------------------------------------------------------
# stream()
# ---------------------------------------------------------------------------

async def test_stream_yields_tokens():
    """stream() must yield at least one token."""
    provider = MockProvider(generate_responses=["Hello from the mock stream."])

    tokens = []
    async for token in provider.stream("Tell me something."):
        tokens.append(token)

    assert len(tokens) > 0


async def test_stream_tokens_reconstruct_full_content():
    """Joining all streamed tokens should reproduce the original response."""
    provider = MockProvider(generate_responses=["Hello world from mock"])

    tokens = []
    async for token in provider.stream("prompt"):
        tokens.append(token)

    full_text = "".join(tokens).strip()
    assert full_text == "Hello world from mock"


async def test_stream_increments_call_count():
    provider = MockProvider()
    assert provider.call_count == 0

    async for _ in provider.stream("prompt"):
        pass  # consume the stream

    assert provider.call_count == 1
