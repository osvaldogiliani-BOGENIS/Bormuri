"""Orchestratore asyncio: collega orecchio, cervello, voce, bocca, occhio e luci."""

from __future__ import annotations

import asyncio
import logging

from bormuri import config
from bormuri.state import State

log = logging.getLogger("bormuri")


class Bormuri:
    def __init__(self, cfg: config.Section):
        # Import qui: i moduli hardware caricano librerie che esistono solo sul Pi.
        from bormuri.audio.capture import Microphone
        from bormuri.audio.playback import Player
        from bormuri.audio.stt import Transcriber
        from bormuri.audio.tts import Voice
        from bormuri.audio.wakeword import WakeWord
        from bormuri.brain.llm import Brain
        from bormuri.display.mouth import Mouth
        from bormuri.lights.link import PicoLink
        from bormuri.lights.scenes import FanController

        self.cfg = cfg
        self.state = State.RIPOSO
        self.mic = Microphone(cfg.audio)
        self.wake = WakeWord(cfg.wakeword)
        self.stt = Transcriber(cfg.stt, cfg.audio.sample_rate)
        self.brain = Brain(cfg.llm)
        self.voice = Voice(cfg.tts)
        self.player = Player(cfg.audio)
        self.mouth = Mouth.from_config(cfg.mouth, self.player.tap)
        self.pico = PicoLink(cfg.lights)
        self.fan = FanController(cfg.fan, self.pico)
        self.button_pressed = asyncio.Event()

    async def set_state(self, state: State) -> None:
        if state != self.state:
            log.info("stato %s -> %s", self.state.value, state.value)
        self.state = state
        self.pico.send_state(state)

    async def converse(self, text: str | None = None) -> None:
        """Un giro completo: ascolta (se serve), pensa, parla."""
        if text is None:
            await self.set_state(State.ASCOLTO)
            audio = await self.mic.record_utterance(self.cfg.stt)
            text = await asyncio.to_thread(self.stt.transcribe, audio)
            log.info("sentito: %r", text)
            if not text.strip():
                await self.set_state(State.RIPOSO)
                return

        await self.set_state(State.PENSIERO)
        reply = await asyncio.to_thread(self.brain.reply, text)
        log.info("risposta: %r", reply)

        samples, rate = await asyncio.to_thread(self.voice.synthesize, reply)
        await self.set_state(State.PARLA)
        await self.player.play(samples, rate, on_level=self.pico.send_level)
        await self.set_state(State.RIPOSO)

    def toggle_mute(self) -> None:
        muted = self.state == State.MUTO
        asyncio.ensure_future(self.set_state(State.RIPOSO if muted else State.MUTO))

    async def listen_loop(self) -> None:
        from bormuri import button

        self._button = button.attach(self.cfg.button, self.button_pressed.set, self.toggle_mute)
        async for _ in self.wake.detections(self.mic, self.button_pressed):
            if self.state == State.RIPOSO:
                await self.converse()

    async def presence_loop(self) -> None:
        if not self.cfg.camera.enabled:
            return
        from bormuri.vision.presence import PresenceDetector

        detector = PresenceDetector(self.cfg.camera)
        async for _ in detector.arrivals():
            if self.state == State.RIPOSO:
                await self.converse("[Qualcuno si è appena avvicinato. Salutalo in una frase.]")

    async def run(self) -> None:
        await self.set_state(State.RIPOSO)
        await asyncio.gather(
            self.mouth.run(),
            self.fan.run(),
            self.listen_loop(),
            self.presence_loop(),
        )


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    asyncio.run(Bormuri(config.load()).run())


if __name__ == "__main__":
    run()
