"""Mode select for Beo4 Infrared (Audio / Video)."""

from __future__ import annotations

from typing import override

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import Beo4ConfigEntry
from .codes import Beo4Destination
from .const import CONF_INFRARED_ENTITY_ID
from .entity import Beo4Entity

PARALLEL_UPDATES = 0

_MODES = {"audio": Beo4Destination.AUDIO, "video": Beo4Destination.VIDEO}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Beo4ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the mode select."""
    if entry.data.get(CONF_INFRARED_ENTITY_ID):
        async_add_entities([Beo4ModeSelect(entry)])


class Beo4ModeSelect(Beo4Entity, RestoreEntity, SelectEntity):
    """Which destination non-source keys go to.

    Source buttons change it, and so can the user. Nothing is sent when it
    changes.
    """

    _attr_translation_key = "mode"
    _attr_options = list(_MODES)

    def __init__(self, entry: Beo4ConfigEntry) -> None:
        """Initialize the select."""
        super().__init__(entry, unique_id_suffix="mode")
        self._runtime = entry.runtime_data

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the last mode and follow changes from source buttons."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) and last.state in _MODES:
            self._runtime.set_destination(_MODES[last.state])
        self.async_on_remove(self._runtime.add_listener(self.async_write_ha_state))

    @property
    @override
    def current_option(self) -> str | None:
        """Return the current mode."""
        for name, destination in _MODES.items():
            if destination == self._runtime.destination:
                return name
        return None

    @override
    async def async_select_option(self, option: str) -> None:
        """Set the mode."""
        self._runtime.set_destination(_MODES[option])
        self.async_write_ha_state()
