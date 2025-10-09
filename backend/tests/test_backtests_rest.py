"""REST API tests for backtests endpoints."""

from http import HTTPStatus

from fastapi.testclient import TestClient

from backend.app.main import app

DEFAULT_LIMIT = 20



def test_post_backtests_idempotency():
    """Ensure POST /backtests is idempotent."""
    client = TestClient(app)
    headers = {"Idempotency-Key": "abc123"}
    body = {
        "strategy_id": "sma_crossover",
        "params": {"fast": 10, "slow": 20},
        "symbol": "AAPL",
        "year": 2024,
    }

    r1 = client.post("/api/v1/backtests", json=body, headers=headers)
    assert r1.status_code == HTTPStatus.ACCEPTED
    j1 = r1.json()
    assert j1["status"] == "QUEUED"
    assert isinstance(j1.get("run_id"), str)

    r2 = client.post("/api/v1/backtests", json=body, headers=headers)
    assert r2.status_code == HTTPStatus.OK
    j2 = r2.json()
    assert j2["status"] == "EXISTS"
    assert j2["run_id"] == j1["run_id"]


def test_post_backtests_missing_symbol_year_returns_400():
    """Validate 400 response when symbol/year are missing."""
    client = TestClient(app)
    headers = {"Idempotency-Key": "xyz789"}
    body = {"strategy_id": "sma_crossover", "params": {"fast": 10, "slow": 20}}

    r = client.post("/api/v1/backtests", json=body, headers=headers)
    assert r.status_code == HTTPStatus.BAD_REQUEST
    j = r.json()
    assert j["error"]["code"] == "BAD_REQUEST"
    assert "dataset_id or (symbol + year)" in j["error"]["message"]


def test_get_backtests_list_empty_defaults():
    """Verify empty list shape and default pagination values."""
    client = TestClient(app)
    r = client.get("/api/v1/backtests")
    assert r.status_code == HTTPStatus.OK
    j = r.json()
    assert j["items"] == []
    assert j["total"] == 0
    assert j["limit"] == DEFAULT_LIMIT
    assert j["offset"] == 0


def test_get_backtest_not_found_shape():
    """Ensure 404 shape when backtest does not exist."""
    client = TestClient(app)
    r = client.get("/api/v1/backtests/does-not-exist")
    assert r.status_code == HTTPStatus.NOT_FOUND
    j = r.json()
    assert j["error"]["code"] == "RUN_NOT_FOUND"
    assert "message" in j["error"]
