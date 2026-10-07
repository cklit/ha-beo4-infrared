"""Beo4 IR protocol encoder and decoder.

Ported from ESPHome's remote_base/beo4_protocol.cpp.

Frame layout (all symbols are a 200 us carrier burst followed by a space,
measured burst-start to burst-start in units of 3125 us):

    ZERO, ZERO, START, <link bit>, <8 destination bits>, <8 command bits>, STOP, burst

Data bits are not sent as absolute values. Each bit is compared with the
previous one: equal -> SAME (2 units), 0->1 -> ONE (3 units), 1->0 -> ZERO
(1 unit). The link bit is always 0 and the "previous bit" starts at 0.

Carrier is 455 kHz, not the usual 36-40 kHz.
"""

from __future__ import annotations

from itertools import pairwise
from typing import override

from infrared_protocols.commands import Command

BEO4_MODULATION_HZ = 455_000

UNIT_US = 3125
CARRIER_US = 200

SYM_ZERO = 1
SYM_SAME = 2
SYM_ONE = 3
SYM_STOP = 4
SYM_START = 5

# 1 link bit + 8 destination bits + 8 command bits
N_DATA_BITS = 17

# Gap inserted between frames when repeat_count > 0. The original Beo4
# repeat timing for held keys is not documented here; adjust if a product
# treats repeats as separate presses.
REPEAT_GAP_US = 100_000

# Periods shorter than this are treated as receiver glitches (TSOP7000
# hiccups) and merged into the surrounding symbol, same as ESPHome.
_GLITCH_US = 1500
# Max deviation from a whole number of units before a symbol is rejected.
_TOLERANCE_US = 1000


def _symbol(timings: list[int], units: int) -> None:
    timings.append(CARRIER_US)
    timings.append(-(units * UNIT_US - CARRIER_US))


def encode_frame(destination: int, command: int) -> list[int]:
    """Return raw timings for one Beo4 frame."""
    timings: list[int] = []
    _symbol(timings, SYM_ZERO)
    _symbol(timings, SYM_ZERO)
    _symbol(timings, SYM_START)
    _symbol(timings, SYM_ZERO)  # link bit, always 0

    code = (destination << 8) | command
    prev = 0
    for shift in range(15, -1, -1):
        bit = (code >> shift) & 1
        if bit == prev:
            _symbol(timings, SYM_SAME)
        elif bit:
            _symbol(timings, SYM_ONE)
        else:
            _symbol(timings, SYM_ZERO)
        prev = bit

    _symbol(timings, SYM_STOP)
    timings.append(CARRIER_US)
    return timings


def _symbols_from_timings(timings: list[int]) -> list[int]:
    """Convert signed raw timings to a list of symbol lengths in units.

    Works on burst-start to burst-start periods so it does not care how the
    receiver split marks and spaces. Invalid periods become 0.
    """
    starts: list[int] = []
    t = 0
    prev_positive = False
    for value in timings:
        positive = value > 0
        if positive and not prev_positive:
            starts.append(t)
        t += abs(value)
        prev_positive = positive

    symbols: list[int] = []
    acc = 0
    for a, b in pairwise(starts):
        acc += b - a
        if acc < _GLITCH_US:
            continue
        units = (acc + UNIT_US // 2) // UNIT_US
        if abs(acc - units * UNIT_US) > _TOLERANCE_US:
            units = 0
        symbols.append(units)
        acc = 0
    return symbols


def decode_frame(timings: list[int]) -> tuple[int, int] | None:
    """Decode the first valid Beo4 frame. Returns (destination, command)."""
    symbols = _symbols_from_timings(timings)
    i = 0
    while i < len(symbols):
        if symbols[i] != SYM_START:
            i += 1
            continue
        data = symbols[i + 1 : i + 1 + N_DATA_BITS]
        stop_idx = i + 1 + N_DATA_BITS
        if len(data) == N_DATA_BITS and stop_idx < len(symbols):
            code = 0
            prev = 0
            ok = True
            for sym in data:
                if sym == SYM_ZERO:
                    prev = 0
                elif sym == SYM_ONE:
                    prev = 1
                elif sym != SYM_SAME:
                    ok = False
                    break
                code = (code << 1) | prev
            if ok and symbols[stop_idx] == SYM_STOP:
                return (code >> 8) & 0xFF, code & 0xFF
        i += 1
    return None


class Beo4Command(Command):
    """Beo4 IR command."""

    destination: int
    command: int

    def __init__(
        self,
        *,
        destination: int,
        command: int,
        repeat_count: int = 0,
        modulation: int = BEO4_MODULATION_HZ,
    ) -> None:
        """Initialize the Beo4 command."""
        if not 0 <= destination <= 0xFF:
            raise ValueError("Beo4 destination must be 0x00..0xFF")
        if not 0 <= command <= 0xFF:
            raise ValueError("Beo4 command must be 0x00..0xFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.destination = destination
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings, including any repeated frames."""
        frame = encode_frame(self.destination, self.command)
        timings = list(frame)
        for _ in range(self.repeat_count):
            timings.append(-REPEAT_GAP_US)
            timings.extend(frame)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Beo4Command | None:
        """Decode raw timings into a command, or None."""
        decoded = decode_frame(timings)
        if decoded is None:
            return None
        return cls(destination=decoded[0], command=decoded[1])

    def __repr__(self) -> str:
        """Return a readable representation."""
        return (
            f"Beo4Command(destination=0x{self.destination:02X}, "
            f"command=0x{self.command:02X}, repeat_count={self.repeat_count})"
        )
