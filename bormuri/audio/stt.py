"""Trascrizione in italiano con faster-whisper, in locale sul Pi."""

from __future__ import annotations

import numpy as np


class Transcriber:
    def __init__(self, cfg, sample_rate: int):
        from faster_whisper import WhisperModel

        assert sample_rate == 16000, "whisper vuole audio a 16 kHz"
        self.language = cfg.language
        self.model = WhisperModel(cfg.model, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(
            audio, language=self.language, beam_size=1, vad_filter=True
        )
        return " ".join(s.text.strip() for s in segments)
