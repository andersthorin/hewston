import time

from fastapi.testclient import TestClient

from backend.app.main import app
import backend.api.routes.backtests as wsmod


def test_ws_heartbeat_hb_event_monkeypatched_interval():
    # Speed up heartbeat for tests
    wsmod.HEARTBEAT_SECONDS = 0.05
    client = TestClient(app)
    with client.websocket_connect("/backtests/test/ws") as ws:
        msg = ws.receive_json()
        assert msg["t"] == "hb"
        ws.close()


def test_ws_err_on_invalid_messages():
    client = TestClient(app)
    with client.websocket_connect("/backtests/test/ws") as ws:
        # Unsupported message type
        ws.send_json({"t": "noop"})
        msg = ws.receive_json()
        assert msg["t"] == "err"
        assert msg["code"] == "VALIDATION"

        # Invalid JSON
        ws.send_text("not json")
        msg2 = ws.receive_json()
        assert msg2["t"] == "err"
        assert msg2["code"] == "VALIDATION"

        # Invalid ctrl cmd
        ws.send_json({"t": "ctrl", "cmd": "bogus"})
        msg3 = ws.receive_json()
        assert msg3["t"] == "err"
        assert msg3["code"] == "VALIDATION"
        ws.close()

