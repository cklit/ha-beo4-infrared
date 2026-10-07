"""Fixtures for Beo4 Infrared tests."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components.infrared import (
    DATA_COMPONENT,
    InfraredEmitterEntity,
    InfraredReceiverEntity,
)
from homeassistant.components.infrared.const import DOMAIN as INFRARED_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from infrared_protocols.commands import Command
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beo4_infrared.const import (
    CONF_DEFAULT_SOURCE,
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)

EMITTER = "infrared.test_ir_emitter"
RECEIVER = "infrared.test_ir_receiver"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components in every test."""


class MockEmitter(InfraredEmitterEntity):
    """Records sent commands."""

    _attr_has_entity_name = True
    _attr_name = "Test IR emitter"

    def __init__(self) -> None:
        """Initialize."""
        self._attr_unique_id = "test_ir_emitter"
        self.sent: list[Command] = []

    async def async_send_command(self, command: Command) -> None:
        """Record the command."""
        self.sent.append(command)


class MockReceiver(InfraredReceiverEntity):
    """Receiver the test can push signals into."""

    _attr_has_entity_name = True
    _attr_name = "Test IR receiver"

    def __init__(self) -> None:
        """Initialize."""
        self._attr_unique_id = "test_ir_receiver"


@pytest.fixture
async def ir_entities(hass: HomeAssistant) -> tuple[MockEmitter, MockReceiver]:
    """Set up the infrared domain with one emitter and one receiver."""
    assert await async_setup_component(hass, INFRARED_DOMAIN, {})
    emitter, receiver = MockEmitter(), MockReceiver()
    await hass.data[DATA_COMPONENT].async_add_entities([emitter, receiver])
    await hass.async_block_till_done()
    return emitter, receiver


@pytest.fixture
def entry_data() -> dict[str, Any]:
    """Config entry data."""
    return {
        CONF_INFRARED_ENTITY_ID: EMITTER,
        CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER,
        CONF_DEFAULT_SOURCE: "RADIO",
    }


@pytest.fixture
async def setup_entry(
    hass: HomeAssistant,
    ir_entities: tuple[MockEmitter, MockReceiver],
    entry_data: dict[str, Any],
) -> MockConfigEntry:
    """Set up the integration."""
    entry = MockConfigEntry(domain=DOMAIN, title="Beo4", data=entry_data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
