"""Uscita audio verso il MAX98357A e buffer condiviso con la bocca.

La bocca non ascolta lo speaker: legge da `AudioTap` gli stessi campioni che
stiamo suonando, nell'istante in cui escono davvero dallo speaker
(ritardo d'uscita compensato). Così la forma d'onda è sincronizzata per costruzione.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Callable

import numpy as np


class AudioTap:
    """Ciò che sta suonando ora, consultabile da un altro task."""

    def __init__(self, latency_s: float = 0.0, clock: Callable[[], float] = time.monotonic):
        self.latency_s = latency_s
        self._clock = clock
        self._lock = threading.Lock()
        self._samples: np.ndarray | None = None
        self._rate = 1
        self._start = 0.0

    def begin(self, samples: np.ndarray, rate: int) -> None:
        with self._lock:
            self._samples = np.asarray(samples, dtype=np.float32)
            self._rate = rate
            self._start = self._clock()

    def end(self) -> None:
        with self._lock:
            self._samples = None

    def window(self, n: int) -> np.ndarray | None:
        """Gli `n` campioni che lo speaker sta emettendo adesso, o None se in silenzio."""
        with self._lock:
            if self._samples is None:
                return None
            pos = int((self._clock() - self._start - self.latency_s) * self._rate)
            if pos < 0 or pos >= len(self._samples):
                return np.zeros(n, dtype=np.float32)
            lo = max(0, pos - n // 2)
            chunk = self._samples[lo : lo + n]
            if len(chunk) < n:
                chunk = np.pad(chunk, (0, n - len(chunk)))
            return chunk


def rms_level(chunk: np.ndarray) -> float:
    """Volume 0..1 di un blocco, per far pulsare le luci rosse con la voce."""
    if chunk.size == 0:
        return 0.0
    return float(min(1.0, np.sqrt(np.mean(np.square(chunk))) * 4.0))


class Player:
    def __init__(self, cfg):
        self.cfg = cfg
        self.tap = AudioTap(latency_s=cfg.output_latency_ms / 1000)

    async def play(
        self,
        samples: np.ndarray,
        rate: int,
        on_level: Callable[[float], None] | None = None,
    ) -> None:
        import sounddevice as sd

        samples = np.asarray(samples, dtype=np.float32) * self.cfg.volume
        done = asyncio.Event()
        loop = asyncio.get_running_loop()
        pos = 0

        def callback(outdata, frames, _time, _status):
            nonlocal pos
            chunk = samples[pos : pos + frames]
            outdata[: len(chunk), 0] = chunk
            outdata[len(chunk) :, 0] = 0
            pos += frames
            if pos >= len(samples):
                raise sd.CallbackStop

        stream = sd.OutputStream(
            samplerate=rate,
            channels=1,
            device=self.cfg.output_device,
            callback=callback,
            finished_callback=lambda: loop.call_soon_threadsafe(done.set),
        )
        # Il driver conosce il proprio ritardo: se lo dichiara, vince sul config.
        if stream.latency:
            self.tap.latency_s = float(stream.latency)
        self.tap.begin(samples, rate)
        with stream:
            level_task = asyncio.create_task(self._levels(on_level)) if on_level else None
            await done.wait()
        self.tap.end()
        if level_task:
            level_task.cancel()
            on_level(0.0)

    async def _levels(self, on_level: Callable[[float], None]) -> None:
        while True:
            chunk = self.tap.window(512)
            if chunk is not None:
                on_level(rms_level(chunk))
            await asyncio.sleep(1 / 30)
