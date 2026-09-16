from fastapi.testclient import TestClient
# TestClient is used to simulate HTTP requests to the FastAPI app in tests without starting a real server.
from app.main import app

# TestClient wraps the FastAPI app and lets you make HTTP requests in tests
# without starting a real server. It triggers the lifespan (startup/shutdown)
# Reliable way is use TestClient as a context manager to ensure proper lifespan handling.
client = TestClient(app)

# test the health check endpoints of the FastAPI application
def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200

# test the structure of the health check response body
def test_health_body_has_required_fields():
    response = client.get("/health")
    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "RegulaFlow"
    assert "version" in body
    assert "environment" in body

# test that the health check response is returned as JSON
def test_health_response_is_json():
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]

# test the readiness check endpoints of the FastAPI application
def test_ready_returns_200():
    response = client.get("/ready")
    assert response.status_code == 200

# test the structure of the readiness check response body
def test_ready_body_is_ok():
    response = client.get("/ready")
    assert response.json()["status"] == "ok"

# test that the correlation ID header is returned on the health check response
def test_correlation_id_header_returned_on_health():
    """
    The middleware should add X-Correlation-ID to every response.
    Even if the client didn't send one, the server generates a UUID.
    """
    response = client.get("/health")
    assert "x-correlation-id" in response.headers
    cid = response.headers["x-correlation-id"]
    assert len(cid) == 36   # UUID4 format

# test that the client-supplied correlation ID is echoed back in the response
def test_client_supplied_correlation_id_is_echoed_back():
    """
    If the client sends X-Correlation-ID, the server must echo the same
    value back. This is how a frontend or upstream service can track its
    own request ID end-to-end.
    """
    response = client.get(
        "/health",
        headers={"X-Correlation-ID": "my-trace-id-123"},
    )
    assert response.headers["x-correlation-id"] == "my-trace-id-123"

# test that FastAPI returns 404 for unknown routes
def test_unknown_route_returns_404():
    """FastAPI should return 404 for routes that don't exist."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
