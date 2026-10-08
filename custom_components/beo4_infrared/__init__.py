"""Beo4 Infrared integration.

Sends Beo4 commands through any emitter on Home Assistant's infrared
platform (for example an ESPHome ir_rf_proxy).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .codes import Beo4Destination

PLATFORMS = [Platform.BUTTON, Platform.SELECT]


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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Beo4ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
