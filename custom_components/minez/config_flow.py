"""Config flow for the MineZ integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any, Protocol

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .api import (
    MinezApiAuthError,
    MinezApiClient,
    MinezApiConnectionError,
    MinezConnectionInfo,
)
from .const import DEFAULT_PORT, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERNAME, default="root"): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class MinezValidationClient(Protocol):
    """Client operations required while validating config flow input."""

    async def async_validate(self) -> dict[str, Any]: ...

    async def async_close(self) -> None: ...


class MinezConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MineZ."""

    VERSION = 1

    def _create_validation_client(
        self, info: MinezConnectionInfo
    ) -> MinezValidationClient:
        """Create a client for validating flow input."""
        return MinezApiClient(info)

    async def _async_validate_input(
        self, user_input: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Validate connection details and return miner identity information."""
        client = self._create_validation_client(
            MinezConnectionInfo(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
        )
        try:
            return await client.async_validate()
        finally:
            await client.async_close()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await self._async_validate_input(user_input)
            except MinezApiAuthError:
                errors["base"] = "invalid_auth"
            except MinezApiConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception validating miner connection")
                errors["base"] = "unknown"

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

    async def async_step_reauth(self, _: Mapping[str, Any]) -> FlowResult:
        """Start reauthentication for an existing config entry."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and store replacement credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            updated_data = {
                **entry.data,
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                await self._async_validate_input(updated_data)
            except MinezApiAuthError:
                errors["base"] = "invalid_auth"
            except MinezApiConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception reauthenticating with miner")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data=updated_data,
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                STEP_REAUTH_DATA_SCHEMA,
                {CONF_USERNAME: entry.data.get(CONF_USERNAME, "root")},
            ),
            errors=errors,
            description_placeholders={CONF_HOST: entry.data[CONF_HOST]},
        )
