"""Remote entity for Beo4 Infrared.

remote.send_command takes key names or raw codes, for anything the
buttons and media player don't cover:

    action: remote.send_command
    target:
      entity_id: remote.beo4
    data:
      command: [radio, volume_up, "0x01:0x0d"]
      device: audio      # optional destination override
      num_repeats: 1
      delay_secs: 0.4
      hold_secs: 1       # optional, sends repeat frames
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any, override

from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_DEVICE,
    ATTR_HOLD_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Beo4ConfigEntry
from .codes import SOURCE_KEYS, Beo4Destination, Beo4Key, parse_destination, parse_key
from .const import CONF_INFRARED_ENTITY_ID, DOMAIN
from .entity import Beo4Entity
from .protocol import REPEAT_GAP_US, Beo4Command, encode_frame

PARALLEL_UPDATES = 1


def _repeats_for_hold(hold_secs: float, destination: int, command: int) -> int:
    frame_us = sum(abs(t) for t in encode_frame(destination, command))
    return max(0, round(hold_secs * 1_000_000 / (frame_us + REPEAT_GAP_US)) - 1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Beo4ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the remote entity."""
    if emitter := entry.data.get(CONF_INFRARED_ENTITY_ID):
        async_add_entities([Beo4Remote(entry, emitter)])


class Beo4Remote(Beo4Entity, InfraredEmitterConsumerEntity, RemoteEntity):
    """Send arbitrary Beo4 keys."""

    _attr_name = None
    _attr_assumed_state = True
    _attr_is_on = True

    def __init__(self, entry: Beo4ConfigEntry, emitter: str) -> None:
        """Initialize the remote."""
        super().__init__(entry, unique_id_suffix="remote")
        self._infrared_emitter_entity_id = emitter
        self._runtime = entry.runtime_data

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Select the default source."""
        await self.async_send_command([self._runtime.default_source.name])
        self._attr_is_on = True
        self.async_write_ha_state()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Send STANDBY."""
        await self.async_send_command([Beo4Key.STANDBY.name])
        self._attr_is_on = False
        self.async_write_ha_state()

    @override
    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send one or more Beo4 keys."""
        override_dest: int | None = None
        if device := kwargs.get(ATTR_DEVICE):
            try:
                override_dest = parse_destination(device)
            except ValueError as err:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_destination",
                    translation_placeholders={"value": device},
                ) from err

        commands: list[tuple[int, int]] = []
        for item in command:
            try:
                dest, code = parse_key(item)
            except ValueError as err:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_command",
                    translation_placeholders={"value": item},
                ) from err
            if dest is None:
                dest = override_dest
            if dest is None and code in SOURCE_KEYS.keys():
                # Source keys go to their own destination and switch the
                # remote's mode, like pressing them on a real Beo4.
                dest = SOURCE_KEYS[Beo4Key(code)]
                self._runtime.destination = Beo4Destination(dest)
            if dest is None:
                dest = self._runtime.destination
            commands.append((dest, code))

        num_repeats: int = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay: float = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)
        hold: float = kwargs.get(ATTR_HOLD_SECS) or 0

        first = True
        for _ in range(num_repeats):
            for dest, code in commands:
                if not first:
                    await asyncio.sleep(delay)
                first = False
                repeats = _repeats_for_hold(hold, dest, code) if hold else 0
                await self._send_command(
                    Beo4Command(destination=dest, command=code, repeat_count=repeats)
                )
