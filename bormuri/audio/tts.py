"""Voce italiana con Piper, più un leggero effetto robotico per il lato Borg."""

from __future__ import annotations

import numpy as np

from bormuri.config import resolve


def borg_effect(samples: np.ndarray, rate: int, amount: float) -> np.ndarray:
    """Modulazione ad anello a 50 Hz più un'eco metallica corta, miscelate di `amount`."""
    if amount <= 0:
        return samples
    t = np.arange(len(samples)) / rate
    ring = samples * np.sin(2 * np.pi * 50 * t)
    delay = int(0.012 * rate)
    echo = np.zeros_like(samples)
    echo[delay:] = samples[:-delay] * 0.5
    wet = ring + echo
    out = (1 - amount) * samples + amount * wet
    peak = np.max(np.abs(out)) or 1.0
    return (out / max(peak, 1.0)).astype(np.float32)


class Voice:
    def __init__(self, cfg):
        from piper import PiperVoice

        self.voice = PiperVoice.load(str(resolve(cfg.voice)))
        self.rate = self.voice.config.sample_rate
        self.amount = cfg.borg_effect

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        chunks = [
            np.frombuffer(c.audio_int16_bytes, dtype=np.int16) for c in self.voice.synthesize(text)
        ]
        pcm = np.concatenate(chunks).astype(np.float32) / 32768.0 if chunks else np.zeros(0)
        return borg_effect(pcm, self.rate, self.amount), self.rate
