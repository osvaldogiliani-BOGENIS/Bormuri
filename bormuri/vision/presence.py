"""Rilevamento volti locale per salutare chi si avvicina. Nessuna registrazione."""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator

from bormuri.vision.camera import Camera


class PresenceDetector:
    def __init__(self, cfg):
        import cv2

        self.cv2 = cv2
        self.cfg = cfg
        self.cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.camera = Camera(cfg.resolution)

    def faces(self) -> int:
        gray = self.cv2.cvtColor(self.camera.frame(), self.cv2.COLOR_RGB2GRAY)
        found = self.cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
        return len(found)

    async def arrivals(self) -> AsyncIterator[int]:
        """Produce il numero di volti quando qualcuno compare dopo un periodo vuoto."""
        present = False
        last_greet = 0.0
        while True:
            n = await asyncio.to_thread(self.faces)
            now = time.monotonic()
            if n and not present and now - last_greet > self.cfg.greet_cooldown_s:
                last_greet = now
                yield n
            present = n > 0
            await asyncio.sleep(self.cfg.presence_interval_s)
