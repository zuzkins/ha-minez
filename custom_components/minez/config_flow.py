"""Config flow for the MineZ integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .api import MinezApiAuthError, MinezApiClient, MinezApiConnectionError, MinezConnectionInfo
from .const import DEFAULT_PORT, DEFAULT_NAME, DOMAIN


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERNAME, default="root"): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class MinezConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MineZ."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = MinezApiClient(
                MinezConnectionInfo(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            )
            try:
                info = await client.async_validate()
            except MinezApiAuthError:
                errors["base"] = "invalid_auth"
            except MinezApiConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            finally:
                await client.async_close()

            if not errors:
                await self.async_set_unique_id(info["uid"] or user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                title = info["hostname"] or info["model"] or DEFAULT_NAME
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
