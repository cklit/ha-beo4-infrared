"""Protocol tests.

esphome_beo4_vectors.json was produced by compiling ESPHome's
remote_base/beo4_protocol.cpp and running its encoder.
"""

import json
from pathlib import Path

import pytest

from custom_components.beo4_infrared.codes import parse_key
from custom_components.beo4_infrared.protocol import (
    BEO4_MODULATION_HZ,
    REPEAT_GAP_US,
    Beo4Command,
    decode_frame,
)

VECTORS = json.loads((Path(__file__).parent / "esphome_beo4_vectors.json").read_text())


@pytest.mark.parametrize(
    "vec", VECTORS, ids=lambda v: f"{v['destination']:02x}{v['command']:02x}"
)
def test_matches_esphome(vec: dict) -> None:
    """Encoder output is identical to ESPHome's."""
    cmd = Beo4Command(destination=vec["destination"], command=vec["command"])
    assert cmd.modulation == vec["carrier"] == BEO4_MODULATION_HZ
    assert cmd.get_raw_timings() == vec["timings"]
    assert decode_frame(vec["timings"]) == (vec["destination"], vec["command"])


def test_repeats() -> None:
    """Repeat frames are appended after a gap and still decode."""
    single = Beo4Command(destination=1, command=0x60).get_raw_timings()
    timings = Beo4Command(destination=1, command=0x60, repeat_count=2).get_raw_timings()
    assert timings == single + [-REPEAT_GAP_US] + single + [-REPEAT_GAP_US] + single
    assert decode_frame(timings) == (1, 0x60)


def test_decode_tolerates_receiver_jitter() -> None:
    """Marks stretched by a demodulator and split by a glitch still decode."""
    clean = Beo4Command(destination=1, command=0x0D).get_raw_timings()
    jittered: list[int] = []
    for i, t in enumerate(clean):
        if t > 0:
            jittered.append(t + 60)
        else:
            jittered.append(t - 60 + (90 if i % 4 == 1 else -90))
    # glitch: short mark inside the start symbol's space
    start_space = 5
    jittered[start_space : start_space + 1] = [-400, 30, jittered[start_space] + 430]
    assert decode_frame(jittered) == (1, 0x0D)


def test_decode_rejects_garbage() -> None:
    """Non-Beo4 timings decode to None."""
    nec = [9000, -4500] + [560, -560] * 32 + [560]
    assert decode_frame(nec) is None
    assert decode_frame([]) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("volume_up", (None, 0x60)),
        ("V.AUX", (None, 0x82)),
        ("0x0d", (None, 0x0D)),
        ("audio:mute", (1, 0x0D)),
        ("0x1b:0x9b", (0x1B, 0x9B)),
    ],
)
def test_parse_key(text: str, expected: tuple) -> None:
    """Key parsing for the remote entity."""
    assert parse_key(text) == expected


@pytest.mark.parametrize("text", ["nope", "0x100", "audio:", "bogus:0x01"])
def test_parse_key_invalid(text: str) -> None:
    """Bad input raises ValueError."""
    with pytest.raises(ValueError):
        parse_key(text)
