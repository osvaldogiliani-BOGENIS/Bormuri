"""Bocca di Bormuri: forma d'onda sull'OLED 0,91" 128x32 nella testa, 30 fps.

I campioni arrivano da `AudioTap`, cioè da ciò che sta suonando lo speaker,
quindi la bocca si muove esattamente con la voce. Qui si calcola solo l'altezza
di ogni colonna; la Plasma 2350 la riceve via USB e la disegna sull'OLED.

Demo al banco (traguardo della Fase 1):

    python -m bormuri.display.mouth demo.wav
    python -m bormuri.display.mouth demo.wav --terminal   # senza Plasma né speaker
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import wave

import numpy as np

from bormuri.audio.playback import AudioTap

WINDOW_SAMPLES = 1024  # ~46 ms a 22 kHz: abbastanza per vedere l'onda "respirare"
MAX_HALF_HEIGHT = 15   # 32 righe: 15 sopra, 15 sotto e la riga centrale


def mouth_columns(samples: np.ndarray | None, width: int = 128, gain: float = 3.0) -> list[int] | None:
    """Semi-altezza dell'onda (0..15 pixel) per ognuna delle `width` colonne.

    None vuol dire silenzio: la bocca mostra la linea di riposo.
    """
    if samples is None or samples.size == 0:
        return None
    usable = samples[: (samples.size // width) * width]
    if usable.size == 0:
        usable = np.pad(samples, (0, width - samples.size))
    peaks = np.abs(usable.reshape(width, -1)).max(axis=1)
    return np.round(np.clip(peaks * gain, 0, 1) * MAX_HALF_HEIGHT).astype(int).tolist()


def render_columns(columns: list[int] | None, width: int = 128, height: int = 32) -> np.ndarray:
    """Disegna le colonne come fa il firmware: barre simmetriche attorno al centro."""
    img = np.zeros((height, width), dtype=bool)
    mid = height // 2
    heights = columns or [0] * width
    for x, h in enumerate(heights[:width]):
        img[max(0, mid - h) : min(height, mid + h + 1), x] = True
    return img


class PlasmaBackend:
    """Manda le colonne alla Plasma, che le disegna sull'OLED nella bocca."""

    def __init__(self, link):
        self.link = link

    def show(self, columns: list[int] | None) -> None:
        self.link.send_mouth(columns)


class TerminalBackend:
    """Anteprima nel terminale: due righe di pixel per carattere."""

    def show(self, columns: list[int] | None) -> None:
        img = render_columns(columns)
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
    def __init__(self, tap: AudioTap, backend, width=128, fps=30, gain=3.0):
        self.tap = tap
        self.backend = backend
        self.width, self.fps, self.gain = width, fps, gain

    @classmethod
    def from_config(cls, cfg, tap: AudioTap, link=None) -> "Mouth":
        backend = PlasmaBackend(link) if link is not None else TerminalBackend()
        return cls(tap, backend, cfg.width, cfg.fps, cfg.gain)

    def frame(self) -> list[int] | None:
        return mouth_columns(self.tap.window(WINDOW_SAMPLES), self.width, self.gain)

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
        mouth = Mouth.from_config(cfg.mouth, tap)
        task = asyncio.create_task(mouth.run())
        tap.begin(samples, rate)  # nessuno speaker: solo la bocca, a tempo reale
        await asyncio.sleep(len(samples) / rate)
        tap.end()
    else:
        from bormuri.audio.playback import Player

        from bormuri.lights.link import PlasmaLink

        player = Player(cfg.audio)
        mouth = Mouth.from_config(cfg.mouth, player.tap, PlasmaLink(cfg.lights))
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
