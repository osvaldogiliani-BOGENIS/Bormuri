"""Protocollo seriale Pi -> Pico 2. Una riga ASCII per comando, terminata da \\n.

    S <STATO>      scena luci: RIPOSO, ASCOLTO, PENSIERO, PARLA, MUTO
    L <0-255>      volume della voce adesso (pulsazione rossa mentre parla)
    F <0-100>      velocità ventola posteriore in percento
    B <0-255>      luminosità massima dei LED
    W <0-255>      luminosità del filo di luci lato Borg
    P              ping; il Pico risponde "OK"

Lo stesso formato è letto da firmware/pico/src/main.cpp: se cambi qui, cambia là.
"""

from __future__ import annotations

import logging
import time

from bormuri.state import State

log = logging.getLogger(__name__)


def encode(cmd: str, value: str | int | None = None) -> bytes:
    if value is None:
        return f"{cmd}\n".encode("ascii")
    return f"{cmd} {value}\n".encode("ascii")


def clamp_byte(x: float) -> int:
    return max(0, min(255, int(round(x * 255))))


class PicoLink:
    """Invia comandi al Pico. Se il Pico manca, registra un avviso e continua."""

    def __init__(self, cfg, serial_factory=None):
        self.cfg = cfg
        self._serial = None
        self._last_level = -1
        self._last_level_t = 0.0
        try:
            if serial_factory is None:
                import serial

                serial_factory = serial.Serial
            self._serial = serial_factory(cfg.serial_port, cfg.baudrate, timeout=0.1)
            self.send("B", clamp_byte(cfg.max_brightness))
        except Exception as exc:  # al banco il Pico può non esserci ancora
            log.warning("Pico non raggiungibile su %s: %s", cfg.serial_port, exc)

    def send(self, cmd: str, value: str | int | None = None) -> None:
        if self._serial is not None:
            self._serial.write(encode(cmd, value))

    def send_state(self, state: State) -> None:
        self.send("S", state.value)

    def send_level(self, level: float) -> None:
        """Volume 0..1. Limitato a ~30 messaggi/s e solo se cambia davvero."""
        value = clamp_byte(level)
        now = time.monotonic()
        if abs(value - self._last_level) < 4 and value != 0:
            return
        if now - self._last_level_t < 1 / 30 and value != 0:
            return
        self._last_level, self._last_level_t = value, now
        self.send("L", value)

    def send_fan(self, percent: int) -> None:
        self.send("F", max(0, min(100, int(percent))))
