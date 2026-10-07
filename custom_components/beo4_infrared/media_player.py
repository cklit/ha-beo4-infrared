"""Media player for Beo4 Infrared."""

from __future__ import annotations

from typing import override

from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import (
    ExtraStoredData,
    RestoredExtraData,
    RestoreEntity,
)

from . import Beo4ConfigEntry
from .codes import SOURCE_BY_NAME, SOURCE_KEYS, SOURCE_NAMES, Beo4Key
from .const import CONF_INFRARED_ENTITY_ID
from .entity import Beo4Entity
from .protocol import Beo4Command

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Beo4ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the media player."""
    if emitter := entry.data.get(CONF_INFRARED_ENTITY_ID):
        async_add_entities([Beo4MediaPlayer(entry, emitter)])


class Beo4MediaPlayer(
    Beo4Entity, InfraredEmitterConsumerEntity, RestoreEntity, MediaPlayerEntity
):
    """Beo4 as a media player. State is assumed, nothing is read back."""

    _attr_name = None
    _attr_assumed_state = True
    _attr_source_list = list(SOURCE_NAMES.values())
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.STOP
    )

    def __init__(self, entry: Beo4ConfigEntry, emitter: str) -> None:
        """Initialize the media player."""
        super().__init__(entry, unique_id_suffix="media_player")
        self._infrared_emitter_entity_id = emitter
        self._runtime = entry.runtime_data
        self._attr_state = MediaPlayerState.ON
        self._attr_source = SOURCE_NAMES[self._runtime.default_source]

    @override
    async def async_added_to_hass(self) -> None:
        """Restore last assumed state and source."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is None:
            return
        self._attr_state = (
            MediaPlayerState.OFF if last.state == STATE_OFF else MediaPlayerState.ON
        )
        extra = await self.async_get_last_extra_data()
        source = extra.as_dict().get("source") if extra else None
        if source in SOURCE_BY_NAME:
            self._attr_source = source
            self._runtime.destination = SOURCE_KEYS[SOURCE_BY_NAME[source]]

    @property
    @override
    def extra_restore_state_data(self) -> ExtraStoredData:
        """Keep the source even while off, when HA drops the attribute."""
        return RestoredExtraData({"source": self._attr_source})

    async def _send_key(self, key: Beo4Key) -> None:
        await self._send_command(
            Beo4Command(destination=self._runtime.destination, command=key)
        )

    async def _select(self, key: Beo4Key) -> None:
        destination = SOURCE_KEYS[key]
        await self._send_command(Beo4Command(destination=destination, command=key))
        self._runtime.destination = destination
        self._attr_source = SOURCE_NAMES[key]
        self._attr_state = MediaPlayerState.ON
        self.async_write_ha_state()

    @override
    async def async_turn_on(self) -> None:
        """Beo4 has no power-on key; selecting a source turns the product on."""
        source = SOURCE_BY_NAME.get(
            self._attr_source or "", self._runtime.default_source
        )
        await self._select(source)

    @override
    async def async_turn_off(self) -> None:
        """Send STANDBY."""
        await self._send_key(Beo4Key.STANDBY)
        self._attr_state = MediaPlayerState.OFF
        self.async_write_ha_state()

    @override
    async def async_select_source(self, source: str) -> None:
        """Send a source key."""
        await self._select(SOURCE_BY_NAME[source])

    @override
    async def async_volume_up(self) -> None:
        """Send volume up."""
        await self._send_key(Beo4Key.VOLUME_UP)

    @override
    async def async_volume_down(self) -> None:
        """Send volume down."""
        await self._send_key(Beo4Key.VOLUME_DOWN)

    @override
    async def async_mute_volume(self, mute: bool) -> None:
        """Send MUTE. It toggles, so the mute argument is ignored."""
        await self._send_key(Beo4Key.MUTE)

    @override
    async def async_media_next_track(self) -> None:
        """Send UP (next track / channel up)."""
        await self._send_key(Beo4Key.UP)

    @override
    async def async_media_previous_track(self) -> None:
        """Send DOWN (previous track / channel down)."""
        await self._send_key(Beo4Key.DOWN)

    @override
    async def async_media_play(self) -> None:
        """Send GO."""
        await self._send_key(Beo4Key.GO)

    @override
    async def async_media_stop(self) -> None:
        """Send STOP."""
        await self._send_key(Beo4Key.STOP)
