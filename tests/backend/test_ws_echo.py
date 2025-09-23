from fastapi.testclient import TestClient

from backend.app.main import app


def test_ws_echo_ctrl_message():
    client = TestClient(app)
    with client.websocket_connect("/backtests/abc/ws") as ws:
        ws.send_json({"t": "ctrl", "cmd": "play"})
        msg = ws.receive_json()
        assert msg["t"] == "ctrl"
        assert msg["cmd"] == "play"
        assert msg.get("echo") is True
        ws.close()

