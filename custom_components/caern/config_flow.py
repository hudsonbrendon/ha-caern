"""Config flow da CAERN (e-mail/senha Firebase)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import (
    CaernApiClient,
    CaernApiCommunicationError,
    CaernApiError,
    CaernAuthError,
)
from .const import DOMAIN


class CaernConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fluxo de configuração via UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pede e-mail e senha do app CAERN (login Firebase)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            try:
                client = CaernApiClient(
                    email=email,
                    password=user_input[CONF_PASSWORD],
                    session=async_get_clientsession(self.hass),
                )
                await client.async_login()
            except CaernAuthError:
                errors["base"] = "invalid_auth"
            except CaernApiCommunicationError:
                errors["base"] = "cannot_connect"
            except CaernApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(client.uid or email)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"CAERN ({email})",
                    data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
            ),
            errors=errors,
        )
