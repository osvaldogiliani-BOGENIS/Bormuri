"""Protocollo seriale PC <-> Plasma 2350. Una riga ASCII per messaggio, terminata da \\n.

PC -> Plasma:
    S <STATO>      scena luci: RIPOSO, ASCOLTO, PENSIERO, PARLA, MUTO, RIUNIONE
    L <0-255>      volume della voce adesso (pulsazione rossa mentre parla)
    M <128 hex>    bocca: una cifra esadecimale per colonna = semi-altezza 0..15
    M              bocca a riposo (linea dritta)
    B <0-255>      luminosità massima dei LED
    P              ping; la Plasma risponde "OK"

Plasma -> PC:
    CIAO bormuri-plasma <versione>   all'avvio
    BTN CORTO | BTN LUNGO            pulsante nascosto (parla / muto)
    T <gradi C>                      temperatura della base ogni 5 s
    OK                               risposta al ping

Se la Plasma non riceve nulla per 10 s va avanti da sola (luci e bocca a riposo),
quindi il PC manda almeno un ping ogni pochi secondi.
Lo stesso formato è letto da firmware/plasma/src/main.cpp: se cambi qui, cambia là.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncIterator, Sequence

from bormuri.state import State

log = logging.getLogger(__name__)

PLASMA_USB_VID = 0x2E8A  # Raspberry Pi (RP2350), usato per trovare la porta da soli
HEARTBEAT_S = 3.0


def encode(cmd: str, value: str | int | None = None) -> bytes:
    if value is None or value == "":
        return f"{cmd}\n".encode("ascii")
    return f"{cmd} {value}\n".encode("ascii")


def encode_mouth(columns: Sequence[int] | None) -> bytes:
    """Colonne 0..15 -> "M 0123...". None o tutto zero -> "M" (linea di riposo)."""
    if columns is None or not any(columns):
        return encode("M")
    return encode("M", "".join("%x" % max(0, min(15, int(c))) for c in columns))


def clamp_byte(x: float) -> int:
    return max(0, min(255, int(round(x * 255))))


def find_port() -> str | None:
    """La prima porta seriale con il VID di Raspberry Pi (COM3, /dev/ttyACM0...)."""
    from serial.tools import list_ports

    for port in list_ports.comports():
        if port.vid == PLASMA_USB_VID:
            return port.device
    return None


class PlasmaLink:
    """Parla con la Plasma. Se manca, registra un avviso e Bormuri continua."""

    def __init__(self, cfg, serial_factory=None):
        self.cfg = cfg
        self._serial = None
        self._last_level = -1
        self._last_level_t = 0.0
        self._last_mouth = b""
        try:
            if serial_factory is None:
                import serial

                serial_factory = serial.Serial
            port = cfg.serial_port or find_port()
            if port is None:
                raise OSError("nessuna Plasma 2350 trovata sulle porte USB")
            self._serial = serial_factory(port, cfg.baudrate, timeout=0.1)
            self.send("B", clamp_byte(cfg.max_brightness))
        except Exception as exc:  # al banco la scheda può non esserci ancora
            log.warning("Plasma non raggiungibile: %s", exc)

    def _write(self, data: bytes) -> None:
        if self._serial is not None:
            self._serial.write(data)

    def send(self, cmd: str, value: str | int | None = None) -> None:
        self._write(encode(cmd, value))

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

    def send_mouth(self, columns: Sequence[int] | None) -> None:
        data = encode_mouth(columns)
        if data == self._last_mouth == b"M\n":
            return  # bocca ferma: inutile ripeterlo 30 volte al secondo
        self._last_mouth = data
        self._write(data)

    async def heartbeat(self) -> None:
        while True:
            self.send("P")
            await asyncio.sleep(HEARTBEAT_S)

    async def events(self) -> AsyncIterator[str]:
        """Righe in arrivo dalla Plasma ("BTN CORTO", "T 31.5"...)."""
        if self._serial is None:
            return
        while True:
            raw = await asyncio.to_thread(self._serial.readline)
            text = raw.decode("ascii", errors="ignore").strip()
            if text:
                yield text
