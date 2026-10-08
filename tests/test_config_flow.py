"""Config flow tests."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beo4_infrared.const import CONF_INFRARED_ENTITY_ID, DOMAIN

from .conftest import EMITTER, MockEmitter


async def test_create_entry(hass: HomeAssistant, emitter: MockEmitter) -> None:
    """Happy path."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Living room", CONF_INFRARED_ENTITY_ID: EMITTER}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living room"
    assert result["data"] == {CONF_INFRARED_ENTITY_ID: EMITTER}


async def test_duplicate_emitter(hass: HomeAssistant, emitter: MockEmitter) -> None:
    """Same emitter twice aborts."""
    MockConfigEntry(
        domain=DOMAIN, data={CONF_INFRARED_ENTITY_ID: EMITTER}
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Beo4", CONF_INFRARED_ENTITY_ID: EMITTER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_no_emitters(hass: HomeAssistant) -> None:
    """Abort when no infrared emitter exists."""
    assert await async_setup_component(hass, "infrared", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_infrared_entities"
