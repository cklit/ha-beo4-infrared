"""Config flow for Beo4 Infrared."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.components.infrared import DOMAIN as INFRARED_DOMAIN
from homeassistant.components.infrared import async_get_emitters
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
)

from .const import CONF_INFRARED_ENTITY_ID, DOMAIN


class Beo4ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Beo4 Infrared."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the emitter."""
        emitters = async_get_emitters(self.hass)
        if not emitters:
            return self.async_abort(reason="no_infrared_entities")

        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_INFRARED_ENTITY_ID: user_input[CONF_INFRARED_ENTITY_ID]}
            )
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={CONF_INFRARED_ENTITY_ID: user_input[CONF_INFRARED_ENTITY_ID]},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Beo4"): TextSelector(),
                vol.Required(CONF_INFRARED_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(
                        domain=INFRARED_DOMAIN, include_entities=emitters
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
