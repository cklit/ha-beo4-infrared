"""Buttons for Beo4 Infrared.

Source buttons send to their own destination and switch the mode. All
other buttons send to the current mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Beo4ConfigEntry
from .codes import SOURCE_KEYS, Beo4Key
from .const import CONF_INFRARED_ENTITY_ID
from .entity import Beo4Entity
from .protocol import Beo4Command

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class Beo4ButtonEntityDescription(ButtonEntityDescription):
    """Describes a Beo4 button."""

    key_code: Beo4Key


def _button(key: Beo4Key) -> Beo4ButtonEntityDescription:
    name = key.name.lower()
    return Beo4ButtonEntityDescription(key=name, translation_key=name, key_code=key)


BUTTONS: tuple[Beo4ButtonEntityDescription, ...] = (
    # Sources
    _button(Beo4Key.TV),
    _button(Beo4Key.DVD),
    _button(Beo4Key.DTV),
    _button(Beo4Key.V_AUX2),
    _button(Beo4Key.CAMERA),
    _button(Beo4Key.PC),
    _button(Beo4Key.V_MEM),
    _button(Beo4Key.RADIO),
    _button(Beo4Key.CD),
    _button(Beo4Key.A_MEM),
    _button(Beo4Key.A_AUX),
    _button(Beo4Key.N_RADIO),
    _button(Beo4Key.N_MUSIC),
    # Transport / volume
    _button(Beo4Key.STANDBY),
    _button(Beo4Key.MUTE),
    _button(Beo4Key.VOLUME_UP),
    _button(Beo4Key.VOLUME_DOWN),
    _button(Beo4Key.GO),
    _button(Beo4Key.STOP),
    _button(Beo4Key.UP),
    _button(Beo4Key.DOWN),
    _button(Beo4Key.LEFT),
    _button(Beo4Key.RIGHT),
    _button(Beo4Key.EXIT),
    # Colour keys
    _button(Beo4Key.RED),
    _button(Beo4Key.GREEN),
    _button(Beo4Key.YELLOW),
    _button(Beo4Key.BLUE),
    # Digits
    *(_button(Beo4Key(n)) for n in range(10)),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Beo4ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    if not (emitter := entry.data.get(CONF_INFRARED_ENTITY_ID)):
        return
    async_add_entities(Beo4Button(entry, emitter, desc) for desc in BUTTONS)


class Beo4Button(Beo4Entity, InfraredEmitterConsumerEntity, ButtonEntity):
    """One Beo4 key."""

    entity_description: Beo4ButtonEntityDescription

    def __init__(
        self,
        entry: Beo4ConfigEntry,
        emitter: str,
        description: Beo4ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(entry, unique_id_suffix=description.key)
        self._infrared_emitter_entity_id = emitter
        self._runtime = entry.runtime_data
        self.entity_description = description

    @property
    @override
    def suggested_object_id(self) -> str:
        """Base the entity ID on the key, not the label ("Vol +" -> volume_up)."""
        return self.entity_description.key

    @override
    async def async_press(self) -> None:
        """Send the key."""
        key = self.entity_description.key_code
        destination = SOURCE_KEYS.get(key, self._runtime.destination)
        await self._send_command(Beo4Command(destination=destination, command=key))
        if key in SOURCE_KEYS:
            self._runtime.set_destination(destination)
