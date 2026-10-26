import wave

import numpy as np

from dm_companion.audio import TrackWriter, rms_level
from dm_companion.config import SAMPLE_RATE


def pcm(samples: int, value: int = 1000) -> bytes:
    return np.full(samples, value, dtype=np.int16).tobytes()


def test_rms_level_silence_and_full_scale():
    assert rms_level(b"") == 0.0
    assert rms_level(pcm(1600, 0)) == 0.0
    assert abs(rms_level(pcm(1600, 32767)) - 1.0) < 1e-3


def test_track_writes_continuous_chunks_without_padding(tmp_path):
    t = TrackWriter(tmp_path / "a.wav", start_offset_s=2.0)
    for i in range(10):
        t.write(pcm(1600), at_s=2.0 + i * 0.1 + 0.05)  # jitter below the threshold
    t.close()
    with wave.open(str(tmp_path / "a.wav")) as w:
        assert w.getframerate() == SAMPLE_RATE
        assert w.getnframes() == 16_000


def test_track_fills_long_gap_with_silence(tmp_path):
    t = TrackWriter(tmp_path / "a.wav", start_offset_s=0.0)
    t.write(pcm(1600), at_s=0.0)  # covers 0.0-0.1 s
    t.write(pcm(1600), at_s=3.1)  # phone was gone for 3 s
    t.close()
    with wave.open(str(tmp_path / "a.wav")) as w:
        frames = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    assert len(frames) == 1600 + 3 * SAMPLE_RATE + 1600
    assert frames[1600:1600 + 3 * SAMPLE_RATE].max() == 0
    assert frames[-1] == 1000


def test_track_drops_odd_trailing_byte(tmp_path):
    t = TrackWriter(tmp_path / "a.wav", start_offset_s=0.0)
    t.write(pcm(10) + b"\x01", at_s=0.0)
    t.close()
    assert t.samples_written == 10
