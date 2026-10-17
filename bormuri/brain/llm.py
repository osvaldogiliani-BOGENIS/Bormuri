"""Personalità di Bormuri tramite l'API di Claude, con memoria breve."""

from __future__ import annotations

from collections import deque

from bormuri.config import resolve


class Brain:
    def __init__(self, cfg):
        import anthropic

        self.client = anthropic.Anthropic()  # legge ANTHROPIC_API_KEY dall'ambiente
        self.model = cfg.model
        self.max_tokens = cfg.max_tokens
        self.system = resolve(cfg.persona_file).read_text(encoding="utf-8")
        self.history: deque[dict] = deque(maxlen=cfg.history_turns * 2)

    def reply(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system,
            messages=list(self.history),
        )
        answer = "".join(b.text for b in response.content if b.type == "text").strip()
        self.history.append({"role": "assistant", "content": answer})
        return answer
