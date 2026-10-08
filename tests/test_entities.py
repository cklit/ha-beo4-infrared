"""Entity tests."""

from __future__ import annotations

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.beo4_infrared.const import CONF_INFRARED_ENTITY_ID, DOMAIN
from custom_components.beo4_infrared.protocol import BEO4_MODULATION_HZ, Beo4Command

from .conftest import EMITTER, MockEmitter

MODE = "select.beo4_mode"

# (entity_id suffix, friendly name, link or None for "current mode", command)
# Copied from the ESPHome config this integration replaces.
EXPECTED = [
    ("tv", "Beo4 TV", 0x00, 0x80),
    ("dvd", "Beo4 DVD", 0x00, 0x86),
    ("dtv", "Beo4 DTV", 0x00, 0x8A),
    ("v_aux2", "Beo4 V.Aux2", 0x00, 0x8D),
    ("camera", "Beo4 Camera", 0x00, 0x87),
    ("pc", "Beo4 PC", 0x00, 0x8B),
    ("v_mem", "Beo4 V.Mem", 0x00, 0x85),
    ("radio", "Beo4 Radio", 0x01, 0x81),
    ("cd", "Beo4 CD", 0x01, 0x92),
    ("a_mem", "Beo4 A.Mem", 0x01, 0x91),
    ("a_aux", "Beo4 A.Aux", 0x01, 0x83),
    ("n_radio", "Beo4 N.Radio", 0x01, 0x93),
    ("n_music", "Beo4 N.Music", 0x01, 0x94),
    ("standby", "Beo4 Standby", None, 0x0C),
    ("mute", "Beo4 Mute", None, 0x0D),
    ("volume_up", "Beo4 Vol +", None, 0x60),
    ("volume_down", "Beo4 Vol -", None, 0x64),
    ("go", "Beo4 Go", None, 0x35),
    ("stop", "Beo4 Stop", None, 0x36),
    ("up", "Beo4 Up", None, 0x1E),
    ("down", "Beo4 Down", None, 0x1F),
    ("left", "Beo4 Left", None, 0x32),
    ("right", "Beo4 Right", None, 0x34),
    ("exit", "Beo4 Exit", None, 0x7F),
    ("red", "Beo4 Red", None, 0xD9),
    ("green", "Beo4 Green", None, 0xD5),
    ("yellow", "Beo4 Yellow", None, 0xD4),
    ("blue", "Beo4 Blue", None, 0xD8),
    *((f"digit_{n}", f"Beo4 {n}", None, n) for n in range(10)),
]


def sent(emitter: MockEmitter) -> list[tuple[int, int]]:
    """(destination, command) for everything sent."""
    out = []
    for cmd in emitter.sent:
        assert isinstance(cmd, Beo4Command)
        assert cmd.modulation == BEO4_MODULATION_HZ
        out.append((cmd.destination, cmd.command))
    return out


async def press(hass: HomeAssistant, key: str) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: f"button.beo4_{key}"},
        blocking=True,
    )


async def set_mode(hass: HomeAssistant, option: str) -> None:
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: MODE, ATTR_OPTION: option},
        blocking=True,
    )


async def test_entities(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Exactly the expected buttons plus the mode select, all enabled."""
    entries = er.async_entries_for_config_entry(entity_registry, setup_entry.entry_id)
    assert sorted(e.entity_id for e in entries) == sorted(
        [f"button.beo4_{key}" for key, *_ in EXPECTED] + [MODE]
    )
    assert all(e.disabled_by is None for e in entries)
    for key, name, *_ in EXPECTED:
        assert hass.states.get(f"button.beo4_{key}").name == name
    state = hass.states.get(MODE)
    assert state.name == "Beo4 Mode"
    assert state.state == "audio"
    assert state.attributes["options"] == ["audio", "video"]


@pytest.mark.parametrize(("key", "name", "link", "cmd"), EXPECTED)
@pytest.mark.parametrize("mode", ["audio", "video"])
async def test_button_codes(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    emitter: MockEmitter,
    mode: str,
    key: str,
    name: str,
    link: int | None,
    cmd: int,
) -> None:
    """Each button sends the same code as the ESPHome config, in both modes."""
    await set_mode(hass, mode)
    await press(hass, key)
    mode_link = {"audio": 0x01, "video": 0x00}[mode]
    assert sent(emitter) == [(mode_link if link is None else link, cmd)]
    if link is not None:
        assert hass.states.get(MODE).state == {0x01: "audio", 0x00: "video"}[link]
    else:
        assert hass.states.get(MODE).state == mode


async def test_sources_switch_mode(
    hass: HomeAssistant, setup_entry: MockConfigEntry, emitter: MockEmitter
) -> None:
    """Volume follows the last source, like a real Beo4."""
    await press(hass, "volume_up")
    await press(hass, "tv")
    await press(hass, "volume_up")
    await press(hass, "cd")
    await press(hass, "volume_down")
    assert sent(emitter) == [
        (0x01, 0x60),
        (0x00, 0x80),
        (0x00, 0x60),
        (0x01, 0x92),
        (0x01, 0x64),
    ]


async def test_mode_restored(hass: HomeAssistant, emitter: MockEmitter) -> None:
    """Mode survives a restart."""
    mock_restore_cache(hass, [State(MODE, "video")])
    entry = MockConfigEntry(
        domain=DOMAIN, title="Beo4", data={CONF_INFRARED_ENTITY_ID: EMITTER}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(MODE).state == "video"
    await press(hass, "mute")
    assert sent(emitter) == [(0x00, 0x0D)]


async def test_emitter_unavailable(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """Buttons go unavailable with the emitter."""
    hass.states.async_set(EMITTER, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get("button.beo4_go").state == STATE_UNAVAILABLE
