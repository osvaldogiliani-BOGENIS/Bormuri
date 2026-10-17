from bormuri.config import Section, load
from bormuri.lights.link import PicoLink, encode
from bormuri.lights.scenes import fan_percent
from bormuri.state import State


class FakeSerial:
    def __init__(self, *_args, **_kwargs):
        self.lines = []

    def write(self, data):
        self.lines.append(data.decode())


def make_link():
    cfg = Section(serial_port="x", baudrate=115200, max_brightness=0.4)
    return PicoLink(cfg, serial_factory=FakeSerial)


def test_encode():
    assert encode("S", "PARLA") == b"S PARLA\n"
    assert encode("P") == b"P\n"


def test_startup_sends_brightness_then_state():
    link = make_link()
    link.send_state(State.ASCOLTO)
    assert link._serial.lines == ["B 102\n", "S ASCOLTO\n"]


def test_level_is_deduplicated():
    link = make_link()
    link.send_level(0.5)
    link.send_level(0.505)
    assert link._serial.lines[-1] == "L 128\n"
    assert link._serial.lines.count("L 128\n") == 1


def test_missing_pico_is_not_fatal():
    def boom(*_a, **_k):
        raise OSError("no device")

    link = PicoLink(Section(serial_port="x", baudrate=1, max_brightness=0.4), serial_factory=boom)
    link.send_state(State.RIPOSO)  # nessuna eccezione


def test_fan_ramp():
    cfg = load().fan
    assert fan_percent(30, cfg) == cfg.min_percent
    assert fan_percent(90, cfg) == cfg.max_percent
    assert cfg.min_percent < fan_percent(62.5, cfg) < cfg.max_percent


def test_config_loads():
    cfg = load()
    assert cfg.mouth.width == 128 and cfg.mouth.height == 32
    assert cfg.button.gpio == 17
