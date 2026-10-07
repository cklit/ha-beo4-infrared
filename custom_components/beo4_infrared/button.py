"""Buttons for Beo4 Infrared."""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Beo4ConfigEntry
from .codes import Beo4Key
from .const import CONF_INFRARED_ENTITY_ID
from .entity import Beo4Entity
from .protocol import Beo4Command

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class Beo4ButtonEntityDescription(ButtonEntityDescription):
    """Describes a Beo4 button."""

    key_code: Beo4Key


def _button(key: Beo4Key, enabled: bool = True) -> Beo4ButtonEntityDescription:
    name = key.name.lower()
    return Beo4ButtonEntityDescription(
        key=name,
        translation_key=name,
        key_code=key,
        entity_registry_enabled_default=enabled,
    )


BUTTONS: tuple[Beo4ButtonEntityDescription, ...] = (
    _button(Beo4Key.STANDBY),
    _button(Beo4Key.UP),
    _button(Beo4Key.DOWN),
    _button(Beo4Key.LEFT),
    _button(Beo4Key.RIGHT),
    _button(Beo4Key.GO),
    _button(Beo4Key.STOP),
    _button(Beo4Key.EXIT),
    _button(Beo4Key.MENU),
    _button(Beo4Key.TEXT, enabled=False),
    _button(Beo4Key.LIGHT, enabled=False),
    _button(Beo4Key.RED, enabled=False),
    _button(Beo4Key.GREEN, enabled=False),
    _button(Beo4Key.YELLOW, enabled=False),
    _button(Beo4Key.BLUE, enabled=False),
    *(_button(Beo4Key(n), enabled=False) for n in range(10)),
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
    """Sends one Beo4 key to the current destination."""

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

    @override
    async def async_press(self) -> None:
        """Send the key."""
        await self._send_command(
            Beo4Command(
                destination=self._runtime.destination,
                command=self.entity_description.key_code,
            )
        )
