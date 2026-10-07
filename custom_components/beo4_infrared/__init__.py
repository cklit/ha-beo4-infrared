"""Beo4 Infrared integration.

Sends Beo4 commands through any emitter on Home Assistant's infrared
platform (for example an ESPHome ir_rf_proxy).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .codes import Beo4Destination

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.SELECT]

# unique_id suffixes of entities from 0.1.0 that no longer exist
_REMOVED_ENTITIES = {
    "media_player",
    "remote",
    "received_command",
    "menu",
    "text",
    "light",
}


@dataclass
class Beo4RuntimeData:
    """Mode shared between entities of one config entry.

    Mirrors a real Beo4: source keys switch the mode, and every other key
    goes to the current mode's destination.
    """

    destination: Beo4Destination = Beo4Destination.AUDIO
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def set_destination(self, destination: Beo4Destination) -> None:
        """Change mode and notify listeners."""
        if destination == self.destination:
            return
        self.destination = destination
        for listener in list(self._listeners):
            listener()

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener. Returns a function that removes it."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)


type Beo4ConfigEntry = ConfigEntry[Beo4RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: Beo4ConfigEntry) -> bool:
    """Set up Beo4 Infrared from a config entry."""
    entry.runtime_data = Beo4RuntimeData()

    ent_reg = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        suffix = (reg_entry.unique_id or "").removeprefix(f"{entry.entry_id}_")
        if suffix in _REMOVED_ENTITIES:
            ent_reg.async_remove(reg_entry.entity_id)
        elif reg_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
            # 0.1.0 created digits and colour keys disabled; all are on now.
            ent_reg.async_update_entity(reg_entry.entity_id, disabled_by=None)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Beo4ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version == 1:
        # 0.1.0 had a default source and an optional receiver. The mode
        # select replaces the first; receiving is dropped.
        data = {
            k: v
            for k, v in entry.data.items()
            if k not in ("default_source", "infrared_receiver_entity_id")
        }
        hass.config_entries.async_update_entry(entry, data=data, version=2)
        _LOGGER.debug("Migrated %s to version 2", entry.entry_id)
    return True
