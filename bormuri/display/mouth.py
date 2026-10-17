"""Bocca di Bormuri: forma d'onda su OLED 0,91" 128x32 SSD1306 a 30-60 fps.

I campioni arrivano da `AudioTap`, cioè da ciò che sta suonando lo speaker,
quindi la bocca si muove esattamente con la voce.

Demo al banco (traguardo della Fase 1):

    python -m bormuri.display.mouth demo.wav
    python -m bormuri.display.mouth demo.wav --terminal   # senza OLED né speaker
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import wave

import numpy as np

from bormuri.audio.playback import AudioTap

WINDOW_SAMPLES = 1024  # ~46 ms a 22 kHz: abbastanza per vedere l'onda "respirare"


def render_waveform(
    samples: np.ndarray | None, width: int = 128, height: int = 32, gain: float = 3.0
) -> np.ndarray:
    """Restituisce un'immagine bool (height, width): per ogni colonna riempie fra min e max.

    Con `samples` None (silenzio) disegna la linea di riposo al centro.
    """
    img = np.zeros((height, width), dtype=bool)
    mid = (height - 1) / 2
    if samples is None or samples.size == 0:
        img[int(round(mid)), :] = True
        return img

    usable = samples[: (samples.size // width) * width]
    if usable.size == 0:
        usable = np.pad(samples, (0, width - samples.size))
    cols = usable.reshape(width, -1)
    lo = np.clip(cols.min(axis=1) * gain, -1, 1)
    hi = np.clip(cols.max(axis=1) * gain, -1, 1)
    # y cresce verso il basso: ampiezza positiva = in alto
    top = np.round(mid - hi * mid).astype(int)
    bottom = np.round(mid - lo * mid).astype(int)
    rows = np.arange(height)[:, None]
    img[(rows >= top) & (rows <= bottom)] = True
    return img


class OledBackend:
    def __init__(self, cfg):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306

        serial = i2c(port=cfg.i2c_port, address=cfg.i2c_address)
        self.device = ssd1306(serial, width=cfg.width, height=cfg.height, rotate=cfg.rotate)

    def show(self, img: np.ndarray) -> None:
        from PIL import Image

        self.device.display(Image.fromarray(img.astype(np.uint8) * 255).convert("1"))


class TerminalBackend:
    """Anteprima nel terminale: due righe di pixel per carattere."""

    def show(self, img: np.ndarray) -> None:
        chars = {(False, False): " ", (True, False): "▀", (False, True): "▄", (True, True): "█"}
        lines = [
            "".join(chars[(bool(a), bool(b))] for a, b in zip(img[y], img[y + 1]))
            for y in range(0, img.shape[0] - 1, 2)
        ]
        sys.stdout.write(f"\x1b[{len(lines)}A" if getattr(self, "_drawn", False) else "")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        self._drawn = True


class Mouth:
    def __init__(self, tap: AudioTap, backend, width=128, height=32, fps=45, gain=3.0):
        self.tap = tap
        self.backend = backend
        self.width, self.height, self.fps, self.gain = width, height, fps, gain

    @classmethod
    def from_config(cls, cfg, tap: AudioTap, terminal: bool = False) -> "Mouth":
        backend = TerminalBackend() if terminal else OledBackend(cfg)
        return cls(tap, backend, cfg.width, cfg.height, cfg.fps, cfg.gain)

    def frame(self) -> np.ndarray:
        return render_waveform(self.tap.window(WINDOW_SAMPLES), self.width, self.height, self.gain)

    async def run(self) -> None:
        period = 1 / self.fps
        loop = asyncio.get_running_loop()
        next_t = loop.time()
        while True:
            self.backend.show(self.frame())
            next_t += period
            await asyncio.sleep(max(0.0, next_t - loop.time()))


def read_wav(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as w:
        rate, width, channels = w.getframerate(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise SystemExit("serve un WAV PCM a 16 bit")
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    return pcm, rate


async def _demo(path: str, terminal: bool) -> None:
    from bormuri import config

    cfg = config.load()
    samples, rate = read_wav(path)
    if terminal:
        tap = AudioTap()
        mouth = Mouth.from_config(cfg.mouth, tap, terminal=True)
        task = asyncio.create_task(mouth.run())
        tap.begin(samples, rate)  # nessuno speaker: solo la bocca, a tempo reale
        await asyncio.sleep(len(samples) / rate)
        tap.end()
    else:
        from bormuri.audio.playback import Player

        player = Player(cfg.audio)
        mouth = Mouth.from_config(cfg.mouth, player.tap)
        task = asyncio.create_task(mouth.run())
        await player.play(samples, rate)
    await asyncio.sleep(0.2)
    task.cancel()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bocca di Bormuri sincronizzata con un WAV")
    parser.add_argument("wav")
    parser.add_argument("--terminal", action="store_true", help="anteprima senza hardware")
    args = parser.parse_args()
    asyncio.run(_demo(args.wav, args.terminal))


if __name__ == "__main__":
    main()
