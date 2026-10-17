"""Pi Camera Module 3 nell'occhio Borg, via picamera2 (installato da apt)."""

from __future__ import annotations

import numpy as np


class Camera:
    def __init__(self, resolution=(640, 480)):
        from picamera2 import Picamera2

        self.cam = Picamera2()
        self.cam.configure(
            self.cam.create_preview_configuration(
                main={"size": tuple(resolution), "format": "RGB888"}
            )
        )
        self.cam.start()

    def frame(self) -> np.ndarray:
        """Un fotogramma RGB. Resta in memoria: niente viene salvato o registrato."""
        return self.cam.capture_array()

    def close(self) -> None:
        self.cam.stop()
