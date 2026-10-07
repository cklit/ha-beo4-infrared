"""Beo4 destination and key codes."""

from __future__ import annotations

from enum import IntEnum


class Beo4Destination(IntEnum):
    """Beo4 destination (link) byte."""

    VIDEO = 0x00
    AUDIO = 0x01


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
    LIST = 0x58
    VOLUME_UP = 0x60
    VOLUME_DOWN = 0x64
    EXIT = 0x7F
    TV = 0x80
    RADIO = 0x81
    A_AUX = 0x83
    V_MEM = 0x85
    DVD = 0x86
    A_MEM = 0x91
    CD = 0x92
    RED = 0xD9
    GREEN = 0xD5
    YELLOW = 0xD4
    BLUE = 0xD8


# Source keys always go to a fixed destination and switch the mode.
SOURCE_KEYS: dict[Beo4Key, Beo4Destination] = {
    Beo4Key.TV: Beo4Destination.VIDEO,
    Beo4Key.DVD: Beo4Destination.VIDEO,
    Beo4Key.V_MEM: Beo4Destination.VIDEO,
    Beo4Key.RADIO: Beo4Destination.AUDIO,
    Beo4Key.CD: Beo4Destination.AUDIO,
    Beo4Key.A_MEM: Beo4Destination.AUDIO,
    Beo4Key.A_AUX: Beo4Destination.AUDIO,
}
