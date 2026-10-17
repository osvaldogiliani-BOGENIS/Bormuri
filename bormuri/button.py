"""Pulsante nascosto su GPIO17: pressione breve = parla, pressione lunga = muto."""

from __future__ import annotations

import asyncio
from typing import Callable


def attach(cfg, on_short: Callable[[], None], on_long: Callable[[], None]):
    """Collega il pulsante; le callback vengono eseguite nel loop asyncio."""
    from gpiozero import Button

    loop = asyncio.get_running_loop()
    button = Button(cfg.gpio, pull_up=True, hold_time=cfg.long_press_s)
    held = False

    def pressed():
        nonlocal held
        held = False

    def on_hold():
        nonlocal held
        held = True
        loop.call_soon_threadsafe(on_long)

    def released():
        if not held:
            loop.call_soon_threadsafe(on_short)

    button.when_pressed = pressed
    button.when_held = on_hold
    button.when_released = released
    return button  # tenerlo vivo: se viene raccolto dal GC il pulsante smette di funzionare
