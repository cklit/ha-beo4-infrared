"""Event entity for Beo4 commands picked up by an infrared receiver.

Needs a receiver that demodulates 455 kHz (TSOP7000 or similar). A normal
38 kHz receiver will not see Beo4 at all.
"""

from __future__ import annotations

import logging
from typing import override

from homeassistant.components.event import EventEntity
from homeassistant.components.infrared import (
    InfraredReceivedSignal,
    InfraredReceiverConsumerEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Beo4ConfigEntry
from .codes import Beo4Destination, Beo4Key, key_name
from .const import CONF_INFRARED_RECEIVER_ENTITY_ID
from .entity import Beo4Entity
from .protocol import Beo4Command

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

EVENT_TYPES = [key.name.lower() for key in Beo4Key] + ["unknown"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Beo4ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entity."""
    if receiver := entry.data.get(CONF_INFRARED_RECEIVER_ENTITY_ID):
        async_add_entities([Beo4ReceivedCommandEvent(entry, receiver)])


class Beo4ReceivedCommandEvent(Beo4Entity, InfraredReceiverConsumerEntity, EventEntity):
    """Fires when a Beo4 frame is decoded."""

    _attr_translation_key = "received_command"
    _attr_event_types = EVENT_TYPES

    def __init__(self, entry: Beo4ConfigEntry, receiver: str) -> None:
        """Initialize the event entity."""
        super().__init__(entry, unique_id_suffix="received_command")
        self._infrared_receiver_entity_id = receiver

    @callback
    @override
    def _handle_signal(self, signal: InfraredReceivedSignal) -> None:
        """Decode and fire."""
        if (cmd := Beo4Command.from_raw_timings(signal.timings)) is None:
            return
        try:
            destination = Beo4Destination(cmd.destination).name.lower()
        except ValueError:
            destination = f"0x{cmd.destination:02x}"
        _LOGGER.debug("Received %r", cmd)
        self._trigger_event(
            key_name(cmd.command),
            {
                "destination": destination,
                "destination_code": cmd.destination,
                "command_code": cmd.command,
            },
        )
        self.async_write_ha_state()
