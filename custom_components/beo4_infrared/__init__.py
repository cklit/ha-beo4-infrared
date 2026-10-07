"""Beo4 Infrared integration.

Sends Beo4 commands through any emitter on Home Assistant's infrared
platform (for example an ESPHome ir_rf_proxy), and optionally decodes Beo4
commands from an infrared receiver.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .codes import SOURCE_KEYS, Beo4Destination, Beo4Key
from .const import CONF_DEFAULT_SOURCE

PLATFORMS = [
    Platform.BUTTON,
    Platform.EVENT,
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
]


@dataclass
class Beo4RuntimeData:
    """State shared between entities of one config entry.

    destination mirrors how a real Beo4 behaves: after a source key is
    pressed, following keys go to that source's destination.
    """

    default_source: Beo4Key
    destination: Beo4Destination


type Beo4ConfigEntry = ConfigEntry[Beo4RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: Beo4ConfigEntry) -> bool:
    """Set up Beo4 Infrared from a config entry."""
    default_source = Beo4Key[entry.data[CONF_DEFAULT_SOURCE]]
    entry.runtime_data = Beo4RuntimeData(
        default_source=default_source,
        destination=SOURCE_KEYS[default_source],
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Beo4ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
