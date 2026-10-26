import os
from dataclasses import dataclass
from pathlib import Path

# server/oracle/config.py -> repo root
ROOT = Path(__file__).resolve().parents[2]

# Phones send 16 kHz mono 16-bit PCM: what Whisper expects, and small enough for Wi-Fi.
SAMPLE_RATE = 16_000


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8443
    data_dir: Path = ROOT / "data"
    cert_dir: Path = ROOT / "certs"
    web_dist: Path = ROOT / "web" / "dist"


def load_settings() -> Settings:
    s = Settings()
    if port := os.environ.get("ORACLE_PORT"):
        s.port = int(port)
    if data := os.environ.get("ORACLE_DATA_DIR"):
        s.data_dir = Path(data)
    return s
