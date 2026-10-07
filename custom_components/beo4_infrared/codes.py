"""Beo4 destination and key codes.

Taken from publicly circulated Beo4 code lists. Not every product reacts to
every code. Anything missing here can still be sent as a hex value through
the remote entity.
"""

from __future__ import annotations

from enum import IntEnum


class Beo4Destination(IntEnum):
    """Beo4 destination (address) byte."""

    VIDEO = 0x00
    AUDIO = 0x01
    V_TAPE = 0x05
    ALL = 0x0F
    LIGHT = 0x1B


class Beo4Key(IntEnum):
    """Beo4 command byte."""

    DIGIT_0 = 0x00
    DIGIT_1 = 0x01
    DIGIT_2 = 0x02
    DIGIT_3 = 0x03
    DIGIT_4 = 0x04
    DIGIT_5 = 0x05
    DIGIT_6 = 0x06
    DIGIT_7 = 0x07
    DIGIT_8 = 0x08
    DIGIT_9 = 0x09
    STANDBY = 0x0C
    MUTE = 0x0D
    UP = 0x1E
    DOWN = 0x1F
    LEFT = 0x32
    RIGHT = 0x34
    GO = 0x35
    STOP = 0x36
    MENU = 0x5C
    VOLUME_UP = 0x60
    VOLUME_DOWN = 0x64
    EXIT = 0x7F
    TV = 0x80
    RADIO = 0x81
    V_AUX = 0x82
    A_AUX = 0x83
    V_MEM = 0x85
    DVD = 0x86
    TEXT = 0x88
    DTV = 0x8A
    PC = 0x8B
    A_MEM = 0x91
    CD = 0x92
    PHONO = 0x93
    LIGHT = 0x9B
    YELLOW = 0xD4
    GREEN = 0xD5
    BLUE = 0xD8
    RED = 0xD9


# Source keys and the destination a Beo4 sends them to. Pressing a source
# key also switches the remote into that destination for following keys.
SOURCE_KEYS: dict[Beo4Key, Beo4Destination] = {
    Beo4Key.TV: Beo4Destination.VIDEO,
    Beo4Key.DTV: Beo4Destination.VIDEO,
    Beo4Key.DVD: Beo4Destination.VIDEO,
    Beo4Key.V_AUX: Beo4Destination.VIDEO,
    Beo4Key.V_MEM: Beo4Destination.VIDEO,
    Beo4Key.PC: Beo4Destination.VIDEO,
    Beo4Key.RADIO: Beo4Destination.AUDIO,
    Beo4Key.CD: Beo4Destination.AUDIO,
    Beo4Key.PHONO: Beo4Destination.AUDIO,
    Beo4Key.A_AUX: Beo4Destination.AUDIO,
    Beo4Key.A_MEM: Beo4Destination.AUDIO,
}

# Display names for source keys, as printed on the Beo4.
SOURCE_NAMES: dict[Beo4Key, str] = {
    Beo4Key.TV: "TV",
    Beo4Key.DTV: "DTV",
    Beo4Key.DVD: "DVD",
    Beo4Key.V_AUX: "V.AUX",
    Beo4Key.V_MEM: "V.MEM",
    Beo4Key.PC: "PC",
    Beo4Key.RADIO: "RADIO",
    Beo4Key.CD: "CD",
    Beo4Key.PHONO: "PHONO",
    Beo4Key.A_AUX: "A.AUX",
    Beo4Key.A_MEM: "A.MEM",
}
SOURCE_BY_NAME: dict[str, Beo4Key] = {v: k for k, v in SOURCE_NAMES.items()}


def _parse_byte(value: str) -> int:
    number = int(value, 0)
    if not 0 <= number <= 0xFF:
        raise ValueError(f"{value} is not a byte")
    return number


def parse_destination(value: str) -> int:
    """Parse a destination name ("audio") or number ("0x01")."""
    name = value.strip().upper().replace(".", "_").replace(" ", "_")
    if name in Beo4Destination.__members__:
        return Beo4Destination[name]
    return _parse_byte(value.strip())


def parse_key(value: str) -> tuple[int | None, int]:
    """Parse a key for the remote entity.

    Accepts a key name ("volume_up", "V.AUX"), a number ("0x60"), or
    "destination:command" ("audio:0x60", "0x01:mute"). Returns
    (destination or None, command).
    """
    destination: int | None = None
    if ":" in value:
        dest_part, value = value.split(":", 1)
        destination = parse_destination(dest_part)
    name = value.strip().upper().replace(".", "_").replace(" ", "_")
    if name in Beo4Key.__members__:
        return destination, Beo4Key[name]
    return destination, _parse_byte(value.strip())


def key_name(command: int) -> str:
    """Return the lowercase key name for a command byte, or "unknown"."""
    try:
        return Beo4Key(command).name.lower()
    except ValueError:
        return "unknown"
