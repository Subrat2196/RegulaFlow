import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_model_provider
from app.main import app
from app.providers.base import ModelProvider, ModelResponse
from app.providers.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(provider: ModelProvider | None = None) -> TestClient:
    """
    Returns a TestClient with the model provider dependency overridden.

    app.dependency_overrides replaces a specific dependency function with
    a lambda that returns a fixed object. FastAPI's DI system picks up
    the override for the duration of the test and restores the original
    when the test finishes (because we call app.dependency_overrides.clear()).
    """
    if provider is not None:
        app.dependency_overrides[get_model_provider] = lambda: provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    """Ensure no override leaks from one test to the next."""
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /compliance/generate — basic success
# ---------------------------------------------------------------------------

def test_generate_returns_200():
    client = _make_client()
    response = client.post("/compliance/generate", json={"prompt": "Summarize GDPR Article 17."})
    assert response.status_code == 200


def test_generate_response_shape():
    client = _make_client()
    body = client.post(
        "/compliance/generate",
        json={"prompt": "Summarize GDPR Article 17."},
    ).json()

    assert body["success"] is True
    assert "data" in body
    data = body["data"]
    assert "content" in data
    assert "model" in data
    assert "input_tokens" in data
    assert "output_tokens" in data
    assert "latency_ms" in data


def test_generate_content_comes_from_provider():
    """The response content must be whatever the provider returns — not hardcoded."""
    provider = MockProvider(generate_responses=["The regulation requires annual audits."])
    client = _make_client(provider)

    body = client.post(
        "/compliance/generate",
        json={"prompt": "What does the regulation require?"},
    ).json()

    assert body["data"]["content"] == "The regulation requires annual audits."


def test_generate_model_field_reflects_provider():
    """model field should say 'mock' when using MockProvider."""
    client = _make_client()
    body = client.post(
        "/compliance/generate",
        json={"prompt": "Test prompt for model field check."},
    ).json()
    assert body["data"]["model"] == "mock"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_generate_rejects_prompt_too_short():
    client = _make_client()
    response = client.post("/compliance/generate", json={"prompt": "Short"})
    assert response.status_code == 422


def test_generate_rejects_missing_prompt():
    client = _make_client()
    response = client.post("/compliance/generate", json={})
    assert response.status_code == 422


def test_generate_rejects_temperature_out_of_range():
    client = _make_client()
    response = client.post(
        "/compliance/generate",
        json={"prompt": "A prompt that is long enough.", "temperature": 1.5},
    )
    assert response.status_code == 422


def test_generate_accepts_system_prompt():
    client = _make_client()
    response = client.post(
        "/compliance/generate",
        json={
            "prompt": "Summarize the retention requirements.",
            "system_prompt": "You are a regulatory compliance expert.",
            "temperature": 0.0,
        },
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Dependency override — the key DI test
# ---------------------------------------------------------------------------

def test_dependency_override_swaps_provider():
    """
    This is the point of dependency injection.

    We give the endpoint a provider that returns a specific string.
    The endpoint's code does not change — it calls provider.generate() and
    gets back whatever the injected provider returns.
    This is how integration tests work without a real API key.
    """
    custom_provider = MockProvider(
        generate_responses=["Custom injected response for this test only."]
    )
    client = _make_client(custom_provider)

    body = client.post(
        "/compliance/generate",
        json={"prompt": "Does the policy cover data retention?"},
    ).json()

    assert body["data"]["content"] == "Custom injected response for this test only."


def test_overrides_are_isolated_between_tests():
    """
    Each test gets a clean dependency graph.
    The autouse fixture calls app.dependency_overrides.clear() after every test.
    This test verifies the default provider is active (not the custom one
    from a previous test).
    """
    client = _make_client()  # no override
    body = client.post(
        "/compliance/generate",
        json={"prompt": "Is the default provider active?"},
    ).json()

    assert body["data"]["model"] == "mock"
    assert body["data"]["content"] == MockProvider.DEFAULT_TEXT
