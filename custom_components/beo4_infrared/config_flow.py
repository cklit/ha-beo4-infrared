"""Config flow for Beo4 Infrared."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.components.infrared import DOMAIN as INFRARED_DOMAIN
from homeassistant.components.infrared import async_get_emitters, async_get_receivers
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .codes import SOURCE_NAMES
from .const import (
    CONF_DEFAULT_SOURCE,
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)

_SOURCE_OPTIONS = [
    SelectOptionDict(value=key.name, label=label) for key, label in SOURCE_NAMES.items()
]


class Beo4ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Beo4 Infrared."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick emitter, optional receiver and default source."""
        emitters = async_get_emitters(self.hass)
        receivers = async_get_receivers(self.hass)
        if not emitters and not receivers:
            return self.async_abort(reason="no_infrared_entities")

        errors: dict[str, str] = {}
        if user_input is not None:
            emitter = user_input.get(CONF_INFRARED_ENTITY_ID)
            receiver = user_input.get(CONF_INFRARED_RECEIVER_ENTITY_ID)
            if not emitter and not receiver:
                errors["base"] = "missing_infrared_entity"
            else:
                if emitter:
                    self._async_abort_entries_match({CONF_INFRARED_ENTITY_ID: emitter})
                if receiver:
                    self._async_abort_entries_match(
                        {CONF_INFRARED_RECEIVER_ENTITY_ID: receiver}
                    )
                name = user_input.pop(CONF_NAME)
                return self.async_create_entry(title=name, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Beo4"): TextSelector(),
                vol.Optional(CONF_INFRARED_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(
                        domain=INFRARED_DOMAIN, include_entities=emitters
                    )
                ),
                vol.Optional(CONF_INFRARED_RECEIVER_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(
                        domain=INFRARED_DOMAIN, include_entities=receivers
                    )
                ),
                vol.Required(CONF_DEFAULT_SOURCE, default="RADIO"): SelectSelector(
                    SelectSelectorConfig(
                        options=_SOURCE_OPTIONS, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
