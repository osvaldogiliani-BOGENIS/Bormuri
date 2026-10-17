"""Parola d'ascolto "Ehi Bormuri" (openWakeWord) oppure pulsante nascosto."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from bormuri.config import resolve


class WakeWord:
    def __init__(self, cfg):
        self.cfg = cfg
        self._model = None

    def _load(self):
        if self._model is None:
            from openwakeword.model import Model

            # Il modello "Ehi Bormuri" va addestrato a parte (notebook openWakeWord,
            # frasi sintetiche italiane) e copiato in models/.
            self._model = Model(wakeword_models=[str(resolve(self.cfg.model))])
        return self._model

    async def detections(self, mic, button: asyncio.Event) -> AsyncIterator[str]:
        """Produce "voce" o "pulsante" ogni volta che Bormuri viene chiamato."""
        model = self._load()
        frames = mic.frames()
        while True:
            frame_task = asyncio.ensure_future(anext(frames))
            button_task = asyncio.ensure_future(button.wait())
            done, _ = await asyncio.wait(
                {frame_task, button_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if button_task in done:
                frame_task.cancel()
                button.clear()
                yield "pulsante"
                continue
            button_task.cancel()
            scores = model.predict(frame_task.result())
            if max(scores.values(), default=0) >= self.cfg.threshold:
                model.reset()
                yield "voce"
