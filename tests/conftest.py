"""Fixtures for Beo4 Infrared tests."""

from __future__ import annotations

import pytest
from homeassistant.components.infrared import DATA_COMPONENT, InfraredEmitterEntity
from homeassistant.components.infrared.const import DOMAIN as INFRARED_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from infrared_protocols.commands import Command
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beo4_infrared.const import CONF_INFRARED_ENTITY_ID, DOMAIN

EMITTER = "infrared.test_ir_emitter"


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


@pytest.fixture
async def emitter(hass: HomeAssistant) -> MockEmitter:
    """Set up the infrared domain with one emitter."""
    assert await async_setup_component(hass, INFRARED_DOMAIN, {})
    entity = MockEmitter()
    await hass.data[DATA_COMPONENT].async_add_entities([entity])
    await hass.async_block_till_done()
    return entity


@pytest.fixture
async def setup_entry(hass: HomeAssistant, emitter: MockEmitter) -> MockConfigEntry:
    """Set up the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, title="Beo4", data={CONF_INFRARED_ENTITY_ID: EMITTER}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
