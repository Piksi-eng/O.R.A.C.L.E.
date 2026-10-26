import json
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from dm_companion.app import create_app
from dm_companion.certs import _cert_covers, ensure_cert
from dm_companion.config import Settings
from dm_companion.session import SessionManager


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", web_dist=tmp_path / "missing-dist")
    manager = SessionManager(settings.data_dir)
    app = create_app(settings, manager, join_url="https://192.168.1.5:8443/join")
    with TestClient(app) as c:
        yield c, manager


def chunk(value: int = 2000) -> bytes:
    return np.full(1600, value, dtype=np.int16).tobytes()


def ping(ws) -> dict:
    """Round-trip a ping so the server has handled every frame sent before it."""
    ws.send_text(json.dumps({"type": "ping"}))
    while True:
        msg = ws.receive_json()
        if msg["type"] == "pong":
            return msg


def test_info_returns_join_url(client):
    c, _ = client
    assert c.get("/api/info").json()["join_url"] == "https://192.168.1.5:8443/join"


def test_pages_explain_missing_build(client):
    c, _ = client
    for path in ("/", "/dm", "/join"):
        r = c.get(path)
        assert r.status_code == 200
        assert "not built" in r.text


def test_mic_requires_player_id(client):
    c, _ = client
    with pytest.raises(Exception):
        with c.websocket_connect("/ws/mic") as ws:
            ws.receive_json()


def test_phone_shows_up_and_disconnects(client):
    c, manager = client
    with c.websocket_connect("/ws/mic?id=abc123&name=Marko&character=Thorin") as ws:
        assert ws.receive_json() == {"type": "status", "recording": False}
        ws.send_bytes(chunk())
        ping(ws)
        players = c.get("/api/state").json()["players"]
        assert players[0]["character"] == "Thorin"
        assert players[0]["connected"] is True
        assert players[0]["level"] > 0
    assert manager.players["abc123"].connected is False


def test_recording_writes_one_wav_per_player_and_manifest(client):
    c, _ = client
    with c.websocket_connect("/ws/mic?id=p1aaaaaa&name=Marko&character=Thorin") as a, \
         c.websocket_connect("/ws/mic?id=p2bbbbbb&name=Ana&character=Lyra Moonwhisper") as b:
        a.receive_json()
        b.receive_json()
        a.send_bytes(chunk())  # before recording: not saved
        ping(a)
        c.post("/api/recording/start")
        for _ in range(5):
            a.send_bytes(chunk(1000))
            b.send_bytes(chunk(3000))
        assert ping(a)["recording"] is True
        ping(b)
        saved = Path(c.post("/api/recording/stop").json()["saved_to"])

    manifest = json.loads((saved / "session.json").read_text(encoding="utf-8"))
    files = sorted(t["file"] for t in manifest["tracks"].values())
    assert files == ["lyra-moonwhisper-p2bbbb.wav", "thorin-p1aaaa.wav"]
    with wave.open(str(saved / "thorin-p1aaaa.wav")) as w:
        assert w.getnframes() == 5 * 1600
    assert manifest["tracks"]["p1aaaaaa"]["duration_s"] == 0.5


def test_phone_is_told_when_recording_starts(client):
    c, _ = client
    with c.websocket_connect("/ws/mic?id=abc123&name=Marko&character=Thorin") as ws:
        ws.receive_json()
        c.post("/api/recording/start")
        ws.send_bytes(chunk())
        assert ws.receive_json() == {"type": "status", "recording": True}
        c.post("/api/recording/stop")


def test_dashboard_socket_pushes_state(client):
    c, _ = client
    with c.websocket_connect("/ws/dm") as ws:
        state = ws.receive_json()
    assert state == {"recording": None, "players": []}


def test_forget_only_removes_disconnected_players(client):
    c, manager = client
    with c.websocket_connect("/ws/mic?id=abc123&name=Marko&character=Thorin") as ws:
        ws.receive_json()
        c.delete("/api/players/abc123")
        assert "abc123" in manager.players
    c.delete("/api/players/abc123")
    assert "abc123" not in manager.players


def test_cert_is_reused_until_ip_changes(tmp_path: Path):
    cert, _ = ensure_cert(tmp_path, ["127.0.0.1", "192.168.1.5"])
    first = cert.read_bytes()
    ensure_cert(tmp_path, ["127.0.0.1", "192.168.1.5"])
    assert cert.read_bytes() == first
    ensure_cert(tmp_path, ["127.0.0.1", "10.0.0.7"])
    assert cert.read_bytes() != first
    assert _cert_covers(cert, ["10.0.0.7"])
