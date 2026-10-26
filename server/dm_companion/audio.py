import wave
from pathlib import Path

import numpy as np

from .config import SAMPLE_RATE

# A pause in a phone's stream longer than this (a reconnect, a locked screen) is filled with
# silence, so every player's file stays on the same session clock. Shorter gaps are network jitter.
GAP_FILL_THRESHOLD_S = 1.0


def rms_level(pcm: bytes) -> float:
    """Loudness of a 16-bit PCM chunk, 0.0 (silence) to 1.0 (full scale)."""
    samples = np.frombuffer(pcm, dtype=np.int16)
    if samples.size == 0:
        return 0.0
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    return float(min(1.0, rms / 32768.0))


class TrackWriter:
    """One player's audio for one recording, as a 16 kHz mono WAV aligned to the session clock."""

    def __init__(self, path: Path, start_offset_s: float):
        self.path = path
        self.start_offset_s = start_offset_s
        self.samples_written = 0
        self._wav = wave.open(str(path), "wb")
        self._wav.setnchannels(1)
        self._wav.setsampwidth(2)
        self._wav.setframerate(SAMPLE_RATE)

    @property
    def end_s(self) -> float:
        return self.start_offset_s + self.samples_written / SAMPLE_RATE

    def write(self, pcm: bytes, at_s: float) -> None:
        """Append a chunk that arrived at `at_s` seconds into the session."""
        if len(pcm) % 2:
            pcm = pcm[:-1]
        gap = at_s - self.end_s
        if gap > GAP_FILL_THRESHOLD_S:
            silence = int(gap * SAMPLE_RATE)
            self._wav.writeframes(b"\x00\x00" * silence)
            self.samples_written += silence
        self._wav.writeframes(pcm)
        self.samples_written += len(pcm) // 2

    def close(self) -> None:
        self._wav.close()
