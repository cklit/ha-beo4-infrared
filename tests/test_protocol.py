"""Protocol tests.

esphome_beo4_vectors.json was produced by compiling ESPHome's
remote_base/beo4_protocol.cpp and running its encoder.
"""

import json
from pathlib import Path

import pytest

from custom_components.beo4_infrared.protocol import (
    BEO4_MODULATION_HZ,
    REPEAT_GAP_US,
    Beo4Command,
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


def test_repeats() -> None:
    """Repeat frames are appended after a gap."""
    single = Beo4Command(destination=1, command=0x60).get_raw_timings()
    timings = Beo4Command(destination=1, command=0x60, repeat_count=2).get_raw_timings()
    assert timings == single + [-REPEAT_GAP_US] + single + [-REPEAT_GAP_US] + single


@pytest.mark.parametrize(("dest", "cmd"), [(-1, 0), (0x100, 0), (0, -1), (0, 0x100)])
def test_out_of_range(dest: int, cmd: int) -> None:
    """Values outside a byte are rejected."""
    with pytest.raises(ValueError):
        Beo4Command(destination=dest, command=cmd)
