"""Health endpoint tests."""

from http import HTTPStatus

from fastapi.testclient import TestClient

from backend.app.main import app


def test_healthz_ok():
    """Return 200 OK with status payload."""
    client = TestClient(app)
    resp = client.get("/api/v1/healthz")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json() == {"status": "ok"}
