"""Entity tests."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.infrared import InfraredReceivedSignal
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_MEDIA_VOLUME_MUTED,
    SERVICE_SELECT_SOURCE,
)
from homeassistant.components.media_player import (
    DOMAIN as MP_DOMAIN,
)
from homeassistant.components.remote import (
    ATTR_COMMAND,
    ATTR_DELAY_SECS,
    ATTR_DEVICE,
    ATTR_HOLD_SECS,
    ATTR_NUM_REPEATS,
    SERVICE_SEND_COMMAND,
)
from homeassistant.components.remote import (
    DOMAIN as REMOTE_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_UP,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.beo4_infrared.const import CONF_INFRARED_RECEIVER_ENTITY_ID
from custom_components.beo4_infrared.protocol import BEO4_MODULATION_HZ, Beo4Command

from .conftest import EMITTER, MockEmitter, MockReceiver

MP = "media_player.beo4"
REMOTE = "remote.beo4"


def sent(emitter: MockEmitter) -> list[tuple[int, int, int]]:
    """(destination, command, repeats) for everything sent."""
    out = []
    for cmd in emitter.sent:
        assert isinstance(cmd, Beo4Command)
        assert cmd.modulation == BEO4_MODULATION_HZ
        out.append((cmd.destination, cmd.command, cmd.repeat_count))
    return out


async def call(
    hass: HomeAssistant, domain: str, service: str, entity_id: str, **data: Any
) -> None:
    await hass.services.async_call(
        domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )


async def test_entities_created(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Expected entities exist; digits and colours are disabled by default."""
    entries = er.async_entries_for_config_entry(entity_registry, setup_entry.entry_id)
    ids = {e.entity_id for e in entries}
    assert {MP, REMOTE, "button.beo4_standby", "event.beo4_received_command"} <= ids
    assert entity_registry.async_get("button.beo4_digit_1").disabled_by is not None
    assert entity_registry.async_get("button.beo4_go").disabled_by is None
    assert hass.states.get(MP).state == STATE_ON
    assert hass.states.get(MP).attributes["source"] == "RADIO"


async def test_media_player_follows_destination(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    ir_entities: tuple[MockEmitter, MockReceiver],
) -> None:
    """Volume goes to audio after RADIO and to video after TV, like a Beo4."""
    emitter, _ = ir_entities
    await call(hass, MP_DOMAIN, SERVICE_VOLUME_UP, MP)
    await call(hass, MP_DOMAIN, SERVICE_SELECT_SOURCE, MP, **{ATTR_INPUT_SOURCE: "TV"})
    await call(hass, MP_DOMAIN, SERVICE_VOLUME_UP, MP)
    await call(hass, BUTTON_DOMAIN, SERVICE_PRESS, "button.beo4_go")
    await call(
        hass, MP_DOMAIN, SERVICE_VOLUME_MUTE, MP, **{ATTR_MEDIA_VOLUME_MUTED: True}
    )
    await call(hass, MP_DOMAIN, SERVICE_TURN_OFF, MP)
    assert sent(emitter) == [
        (0x01, 0x60, 0),
        (0x00, 0x80, 0),
        (0x00, 0x60, 0),
        (0x00, 0x35, 0),
        (0x00, 0x0D, 0),
        (0x00, 0x0C, 0),
    ]
    assert hass.states.get(MP).state == STATE_OFF

    emitter.sent.clear()
    await call(hass, MP_DOMAIN, SERVICE_TURN_ON, MP)
    assert sent(emitter) == [(0x00, 0x80, 0)]
    assert hass.states.get(MP).state == STATE_ON
    assert hass.states.get(MP).attributes["source"] == "TV"


async def test_media_player_restores_source_while_off(
    hass: HomeAssistant, ir_entities: tuple[MockEmitter, MockReceiver], entry_data: dict
) -> None:
    """Off state and last source survive a restart; volume goes to video."""
    emitter, _ = ir_entities
    mock_restore_cache_with_extra_data(
        hass, [(State(MP, STATE_OFF), {"source": "DVD"})]
    )
    entry = MockConfigEntry(domain="beo4_infrared", title="Beo4", data=entry_data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(MP).state == STATE_OFF

    await call(hass, MP_DOMAIN, SERVICE_VOLUME_UP, MP)
    await call(hass, MP_DOMAIN, SERVICE_TURN_ON, MP)
    assert sent(emitter) == [(0x00, 0x60, 0), (0x00, 0x86, 0)]


async def test_remote_send_command(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    ir_entities: tuple[MockEmitter, MockReceiver],
) -> None:
    """Names, hex, destination prefixes, device override, repeats and hold."""
    emitter, _ = ir_entities
    await call(
        hass,
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        REMOTE,
        **{ATTR_COMMAND: ["cd", "volume_up", "0x1b:0x9b", "0x05"], ATTR_DELAY_SECS: 0},
    )
    assert sent(emitter) == [
        (0x01, 0x92, 0),
        (0x01, 0x60, 0),
        (0x1B, 0x9B, 0),
        (0x01, 0x05, 0),
    ]

    emitter.sent.clear()
    await call(
        hass,
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        REMOTE,
        **{
            ATTR_COMMAND: ["mute"],
            ATTR_DEVICE: "video",
            ATTR_NUM_REPEATS: 2,
            ATTR_DELAY_SECS: 0,
        },
    )
    assert sent(emitter) == [(0x00, 0x0D, 0), (0x00, 0x0D, 0)]

    emitter.sent.clear()
    await call(
        hass,
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        REMOTE,
        **{ATTR_COMMAND: ["volume_down"], ATTR_HOLD_SECS: 1},
    )
    ((dest, cmd, repeats),) = sent(emitter)
    assert (dest, cmd) == (0x01, 0x64)
    assert repeats >= 3


@pytest.mark.parametrize(
    "data",
    [{ATTR_COMMAND: ["not_a_key"]}, {ATTR_COMMAND: ["mute"], ATTR_DEVICE: "kitchen"}],
)
async def test_remote_invalid(
    hass: HomeAssistant, setup_entry: MockConfigEntry, data: dict[str, Any]
) -> None:
    """Bad keys or destinations raise a validation error."""
    with pytest.raises(ServiceValidationError):
        await call(hass, REMOTE_DOMAIN, SERVICE_SEND_COMMAND, REMOTE, **data)


async def test_event_from_receiver(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    ir_entities: tuple[MockEmitter, MockReceiver],
) -> None:
    """A decoded Beo4 frame fires the event entity; garbage does not."""
    _, receiver = ir_entities
    ent = "event.beo4_received_command"
    receiver._handle_received_signal(
        InfraredReceivedSignal(timings=[9000, -4500, 560], modulation=None)
    )
    await hass.async_block_till_done()
    assert hass.states.get(ent).attributes["event_type"] is None

    timings = Beo4Command(destination=0x01, command=0x60).get_raw_timings()
    receiver._handle_received_signal(InfraredReceivedSignal(timings=timings))
    await hass.async_block_till_done()
    attrs = hass.states.get(ent).attributes
    assert attrs["event_type"] == "volume_up"
    assert attrs["destination"] == "audio"
    assert attrs["command_code"] == 0x60

    timings = Beo4Command(destination=0x42, command=0xEE).get_raw_timings()
    receiver._handle_received_signal(InfraredReceivedSignal(timings=timings))
    await hass.async_block_till_done()
    attrs = hass.states.get(ent).attributes
    assert attrs["event_type"] == "unknown"
    assert attrs["destination"] == "0x42"


async def test_emitter_unavailable(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    ir_entities: tuple[MockEmitter, MockReceiver],
) -> None:
    """Entities go unavailable with the emitter."""
    hass.states.async_set(EMITTER, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get(MP).state == STATE_UNAVAILABLE
    assert hass.states.get("button.beo4_go").state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    "entry_data",
    [
        {
            CONF_INFRARED_RECEIVER_ENTITY_ID: "infrared.test_ir_receiver",
            "default_source": "TV",
        }
    ],
)
async def test_receiver_only(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Without an emitter only the event entity is created."""
    entries = er.async_entries_for_config_entry(entity_registry, setup_entry.entry_id)
    assert [e.domain for e in entries] == ["event"]
