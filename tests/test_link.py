import asyncio

from bormuri.config import Section, load
from bormuri.lights.link import PlasmaLink, encode, encode_mouth
from bormuri.state import State


class FakeSerial:
    def __init__(self, *_args, **_kwargs):
        self.lines = []
        self.incoming = [b"CIAO bormuri-plasma 2\r\n", b"", b"BTN CORTO\r\n"]

    def write(self, data):
        self.lines.append(data.decode())

    def readline(self):
        if not self.incoming:
            raise EOFError
        return self.incoming.pop(0)


def make_link():
    cfg = Section(serial_port="x", baudrate=115200, max_brightness=0.4)
    return PlasmaLink(cfg, serial_factory=FakeSerial)


def test_encode():
    assert encode("S", "PARLA") == b"S PARLA\n"
    assert encode("P") == b"P\n"


def test_encode_mouth():
    assert encode_mouth(None) == b"M\n"
    assert encode_mouth([0] * 128) == b"M\n"
    line = encode_mouth([15, 3, 20, -1] + [0] * 124)
    assert line.startswith(b"M f3f0") and len(line) == 2 + 128 + 1


def test_startup_sends_brightness_then_state():
    link = make_link()
    link.send_state(State.RIUNIONE)
    assert link._serial.lines == ["B 102\n", "S RIUNIONE\n"]


def test_rest_mouth_is_sent_once():
    link = make_link()
    link.send_mouth(None)
    link.send_mouth(None)
    link.send_mouth([1] * 128)
    link.send_mouth(None)
    assert [l[0] for l in link._serial.lines[1:]] == ["M", "M", "M"]


def test_level_is_deduplicated():
    link = make_link()
    link.send_level(0.5)
    link.send_level(0.505)
    assert link._serial.lines.count("L 128\n") == 1


def test_events_skip_blank_lines():
    link = make_link()

    async def first_two():
        out = []
        async for e in link.events():
            out.append(e)
            if len(out) == 2:
                return out

    assert asyncio.run(first_two()) == ["CIAO bormuri-plasma 2", "BTN CORTO"]


def test_missing_plasma_is_not_fatal():
    def boom(*_a, **_k):
        raise OSError("no device")

    link = PlasmaLink(Section(serial_port="x", baudrate=1, max_brightness=0.4), serial_factory=boom)
    link.send_state(State.RIPOSO)  # nessuna eccezione
    link.send_mouth([3] * 128)


def test_config_loads():
    cfg = load()
    assert cfg.mouth.width == 128 and cfg.mouth.height == 32
    assert cfg.lights.serial_port is None
