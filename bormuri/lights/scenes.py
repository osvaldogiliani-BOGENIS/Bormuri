"""Logica lato Pi delle luci e della ventola.

Le animazioni vere girano sul Pico (firmware/pico): qui si decide solo *cosa*
mostrare. La ventola segue la temperatura del Pi, che il Pico non può leggere.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from bormuri.state import State

# Descrizione delle scene, per riferimento: l'implementazione è in main.cpp.
SCENES = {
    State.RIPOSO: "respiro lento azzurro",
    State.ASCOLTO: "scansione blu",
    State.PENSIERO: "arancio che rincorre",
    State.PARLA: "rosso che pulsa con la voce",
    State.MUTO: "rosso fisso al minimo",
}

THERMAL_ZONE = Path("/sys/class/thermal/thermal_zone0/temp")


def fan_percent(temp_c: float, cfg) -> int:
    """Rampa lineare fra temp_low_c (min_percent) e temp_high_c (max_percent)."""
    if temp_c <= cfg.temp_low_c:
        return cfg.min_percent
    if temp_c >= cfg.temp_high_c:
        return cfg.max_percent
    k = (temp_c - cfg.temp_low_c) / (cfg.temp_high_c - cfg.temp_low_c)
    return round(cfg.min_percent + k * (cfg.max_percent - cfg.min_percent))


def cpu_temp_c() -> float | None:
    try:
        return int(THERMAL_ZONE.read_text()) / 1000
    except (OSError, ValueError):
        return None


class FanController:
    def __init__(self, cfg, link):
        self.cfg = cfg
        self.link = link

    async def run(self, interval_s: float = 5.0) -> None:
        # Si invia sempre, anche se invariato: fa da battito per il Pico, che dopo
        # 10 s senza messaggi va in modalità sicura (ventola al massimo).
        while True:
            temp = cpu_temp_c()
            percent = fan_percent(temp, self.cfg) if temp is not None else self.cfg.max_percent
            self.link.send_fan(percent)
            await asyncio.sleep(interval_s)
