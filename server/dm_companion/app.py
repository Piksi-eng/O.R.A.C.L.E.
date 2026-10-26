import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import SAMPLE_RATE, Settings
from .session import SessionManager

DASHBOARD_PUSH_INTERVAL_S = 0.1

NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>DM Companion</title>
<body style="font-family:sans-serif;background:#111;color:#eee;padding:2rem">
<h1>The web app is not built yet</h1>
<p>Run <code>npm install</code> and <code>npm run build</code> in the <code>web</code> folder,
or run <code>scripts\\setup.ps1</code>, then reload.</p></body>"""


def create_app(settings: Settings, manager: SessionManager, join_url: str = "") -> FastAPI:
    app = FastAPI(title="DM Companion")
    app.state.manager = manager

    @app.get("/api/info")
    def info():
        return {"join_url": join_url, "sample_rate": SAMPLE_RATE}

    @app.get("/api/state")
    def state():
        return manager.snapshot()

    @app.post("/api/recording/start")
    def start_recording():
        rec = manager.start_recording()
        return {"recording": rec.dir.name}

    @app.post("/api/recording/stop")
    def stop_recording():
        rec_dir = manager.stop_recording()
        return {"saved_to": str(rec_dir) if rec_dir else None}

    @app.delete("/api/players/{player_id}")
    def forget_player(player_id: str):
        manager.forget(player_id)
        return {"ok": True}

    @app.websocket("/ws/mic")
    async def mic(ws: WebSocket):
        """A player's phone: binary frames are 16 kHz mono int16 PCM, text frames are JSON control messages."""
        player_id = ws.query_params.get("id", "")
        if not player_id:
            await ws.close(code=1008)
            return
        await ws.accept()
        manager.connect(player_id, ws.query_params.get("name", ""), ws.query_params.get("character", ""))
        told_recording = manager.recording is not None
        try:
            await ws.send_json({"type": "status", "recording": told_recording})
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    manager.on_audio(player_id, msg["bytes"])
                elif msg.get("text"):
                    data = json.loads(msg["text"])
                    if data.get("type") == "ping":
                        await ws.send_json({"type": "pong", "recording": manager.recording is not None})
                recording = manager.recording is not None
                if recording != told_recording:
                    await ws.send_json({"type": "status", "recording": recording})
                    told_recording = recording
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(player_id)

    @app.websocket("/ws/dm")
    async def dm(ws: WebSocket):
        """The DM dashboard: the table's state, pushed ten times a second."""
        await ws.accept()

        async def push():
            try:
                while True:
                    await ws.send_json(manager.snapshot())
                    await asyncio.sleep(DASHBOARD_PUSH_INTERVAL_S)
            except (WebSocketDisconnect, RuntimeError):
                pass

        pusher = asyncio.create_task(push())
        try:
            # Reading is what notices the dashboard tab closing; sending to a gone client can't.
            while (await ws.receive())["type"] != "websocket.disconnect":
                pass
        except WebSocketDisconnect:
            pass
        finally:
            pusher.cancel()

    _mount_web(app, settings.web_dist)
    return app


def _mount_web(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"

    async def spa():
        if index.exists():
            return FileResponse(index)
        return HTMLResponse(NOT_BUILT)

    for path in ("/", "/dm", "/join"):
        app.add_api_route(path, spa, include_in_schema=False)
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist), name="web")
