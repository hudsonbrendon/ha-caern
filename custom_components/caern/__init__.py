"""Integração CAERN para Home Assistant."""

from __future__ import annotations

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import CaernApiClient
from .const import DOMAIN
from .coordinator import CaernConfigEntry, CaernDataUpdateCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Registra os serviços do domínio."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CaernConfigEntry) -> bool:
    """Configura a integração a partir de um config entry."""
    client = CaernApiClient(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )
    await client.async_login()

    coordinator = CaernDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CaernConfigEntry) -> bool:
    """Descarrega o config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
