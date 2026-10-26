"""Who is at the table, and the recording in progress."""

import datetime
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .audio import TrackWriter, rms_level
from .config import SAMPLE_RATE

# A phone that has sent nothing for this long shows as silent on the dashboard.
LEVEL_STALE_S = 0.5


@dataclass
class Player:
    id: str
    name: str
    character: str
    connected: bool = False
    level: float = 0.0
    last_audio: float = 0.0  # time.monotonic() of the last chunk


@dataclass
class Recording:
    dir: Path
    started_at: float  # time.monotonic()
    started_wall: str
    tracks: dict[str, TrackWriter] = field(default_factory=dict)

    def elapsed(self, now: float) -> float:
        return now - self.started_at


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "player"


class SessionManager:
    def __init__(self, data_dir: Path, clock=time.monotonic):
        self.data_dir = data_dir
        self.clock = clock
        self.players: dict[str, Player] = {}
        self.recording: Recording | None = None

    # Players

    def connect(self, player_id: str, name: str, character: str) -> Player:
        p = self.players.get(player_id)
        if p is None:
            p = self.players[player_id] = Player(player_id, name, character)
        p.name, p.character, p.connected = name, character, True
        return p

    def disconnect(self, player_id: str) -> None:
        if p := self.players.get(player_id):
            p.connected = False
            p.level = 0.0

    def forget(self, player_id: str) -> None:
        p = self.players.get(player_id)
        if p and not p.connected:
            del self.players[player_id]

    def on_audio(self, player_id: str, pcm: bytes) -> None:
        p = self.players.get(player_id)
        if p is None:
            return
        now = self.clock()
        p.level = rms_level(pcm)
        p.last_audio = now
        rec = self.recording
        if rec is None:
            return
        at = rec.elapsed(now)
        track = rec.tracks.get(player_id)
        if track is None:
            filename = f"{_slug(p.character or p.name)}-{player_id[:6]}.wav"
            track = rec.tracks[player_id] = TrackWriter(rec.dir / filename, start_offset_s=at)
        track.write(pcm, at)

    # Recording

    def start_recording(self) -> Recording:
        if self.recording:
            return self.recording
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        rec_dir = self.data_dir / "sessions" / stamp
        rec_dir.mkdir(parents=True, exist_ok=True)
        self.recording = Recording(rec_dir, self.clock(), datetime.datetime.now().isoformat(timespec="seconds"))
        return self.recording

    def stop_recording(self) -> Path | None:
        rec = self.recording
        if rec is None:
            return None
        self.recording = None
        duration = rec.elapsed(self.clock())
        tracks = {}
        for pid, track in rec.tracks.items():
            track.close()
            p = self.players.get(pid)
            tracks[pid] = {
                "name": p.name if p else "",
                "character": p.character if p else "",
                "file": track.path.name,
                "start_offset_s": round(track.start_offset_s, 3),
                "duration_s": round(track.samples_written / SAMPLE_RATE, 3),
            }
        manifest = {"started": rec.started_wall, "duration_s": round(duration, 3), "tracks": tracks}
        (rec.dir / "session.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return rec.dir

    # Dashboard

    def snapshot(self) -> dict:
        now = self.clock()
        rec = self.recording
        return {
            "recording": None if rec is None else {"elapsed_s": round(rec.elapsed(now), 1), "dir": rec.dir.name},
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "character": p.character,
                    "connected": p.connected,
                    "level": p.level if now - p.last_audio < LEVEL_STALE_S else 0.0,
                    "recording": rec is not None and p.id in rec.tracks,
                }
                for p in self.players.values()
            ],
        }
