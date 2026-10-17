"""Microfono USB nella punta dell'antenna Borg (ALSA via sounddevice)."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import numpy as np

FRAME_MS = 80  # openWakeWord lavora a blocchi da 80 ms a 16 kHz


class Microphone:
    def __init__(self, cfg):
        self.rate = cfg.sample_rate
        self.device = cfg.input_device
        self.frame = self.rate * FRAME_MS // 1000
        self._queue: asyncio.Queue[np.ndarray] | None = None
        self._stream = None

    def _ensure_stream(self) -> None:
        if self._stream is not None:
            return
        import sounddevice as sd

        loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=50)

        def callback(indata, _frames, _time, _status):
            block = indata[:, 0].astype(np.int16).copy()
            loop.call_soon_threadsafe(self._put, block)

        self._stream = sd.InputStream(
            samplerate=self.rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame,
            device=self.device,
            callback=callback,
        )
        self._stream.start()

    def _put(self, block: np.ndarray) -> None:
        if self._queue.full():
            self._queue.get_nowait()  # meglio perdere un blocco vecchio che restare indietro
        self._queue.put_nowait(block)

    async def frames(self) -> AsyncIterator[np.ndarray]:
        self._ensure_stream()
        while True:
            yield await self._queue.get()

    def drain(self) -> None:
        if self._queue:
            while not self._queue.empty():
                self._queue.get_nowait()

    async def record_utterance(self, stt_cfg) -> np.ndarray:
        """Registra finché non c'è `silence_ms` di silenzio (o `max_seconds`)."""
        self.drain()
        blocks: list[np.ndarray] = []
        silent_ms = 0
        heard_voice = False
        max_blocks = stt_cfg.max_seconds * 1000 // FRAME_MS
        async for block in self.frames():
            blocks.append(block)
            loud = np.abs(block).mean() > 500  # soglia grezza, da tarare al banco
            heard_voice |= loud
            silent_ms = 0 if loud else silent_ms + FRAME_MS
            if (heard_voice and silent_ms >= stt_cfg.silence_ms) or len(blocks) >= max_blocks:
                break
        return np.concatenate(blocks).astype(np.float32) / 32768.0
