from fastapi.testclient import TestClient

from backend.app.main import app


def test_post_backtests_idempotency():
    client = TestClient(app)
    headers = {"Idempotency-Key": "abc123"}
    body = {"strategy_id": "sma_crossover", "params": {"fast": 10, "slow": 20}}

    r1 = client.post("/backtests", json=body, headers=headers)
    assert r1.status_code == 202
    j1 = r1.json()
    assert j1["status"] == "QUEUED"
    assert isinstance(j1.get("run_id"), str)

    r2 = client.post("/backtests", json=body, headers=headers)
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["status"] == "EXISTS"
    assert j2["run_id"] == j1["run_id"]


def test_get_backtests_list_empty_defaults():
    client = TestClient(app)
    r = client.get("/backtests")
    assert r.status_code == 200
    j = r.json()
    assert j["items"] == []
    assert j["total"] == 0
    assert j["limit"] == 20
    assert j["offset"] == 0


def test_get_backtest_not_found_shape():
    client = TestClient(app)
    r = client.get("/backtests/does-not-exist")
    assert r.status_code == 404
    j = r.json()
    assert j["error"]["code"] == "RUN_NOT_FOUND"
    assert "message" in j["error"]

