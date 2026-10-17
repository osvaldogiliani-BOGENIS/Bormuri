import numpy as np

from bormuri.audio.playback import AudioTap, rms_level
from bormuri.display.mouth import mouth_columns, render_columns


def test_silence_is_rest_line():
    assert mouth_columns(None) is None
    img = render_columns(None)
    assert img.shape == (32, 128)
    assert img.sum() == 128 and img[16].all()


def test_loud_sine_fills_full_height():
    t = np.arange(1024) / 22050
    cols = mouth_columns(np.sin(2 * np.pi * 440 * t).astype(np.float32), gain=3.0)
    assert len(cols) == 128 and max(cols) == 15
    img = render_columns(cols)
    assert img[1].any() and img[31].any()


def test_quiet_signal_stays_near_middle():
    cols = mouth_columns(np.full(1024, 0.01, dtype=np.float32), gain=1.0)
    assert max(cols) == 0


def test_short_window_is_padded():
    assert len(mouth_columns(np.ones(10, dtype=np.float32))) == 128


def test_tap_compensates_output_latency():
    now = [100.0]
    tap = AudioTap(latency_s=0.5, clock=lambda: now[0])
    samples = np.arange(1000, dtype=np.float32)
    tap.begin(samples, rate=100)

    now[0] = 100.2  # lo speaker non ha ancora emesso nulla
    assert not tap.window(4).any()

    now[0] = 101.0  # sentito adesso: campione (1.0 - 0.5) * 100 = 50
    assert tap.window(4).tolist() == [48, 49, 50, 51]

    tap.end()
    assert tap.window(4) is None


def test_rms_level_bounds():
    assert rms_level(np.zeros(10)) == 0
    assert rms_level(np.ones(10)) == 1.0
