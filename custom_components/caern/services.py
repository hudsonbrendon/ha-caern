"""Serviços (ações) da integração CAERN."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .api import CaernApiClient, CaernApiError
from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import CaernConfigEntry

SERVICE_AUTOLEITURA = "enviar_autoleitura"
SERVICE_ADD_IMOVEL = "adicionar_imovel"
SERVICE_DEL_IMOVEL = "remover_imovel"
SERVICE_SEGUNDA_VIA = "segunda_via"

ATTR_ENTRY = "config_entry_id"
ATTR_MATRICULA = "matricula"
ATTR_LEITURA = "leitura"
ATTR_CPF_CNPJ = "cpf_cnpj"
ATTR_ID_CONTA = "id_conta"

_ENTRY = {vol.Optional(ATTR_ENTRY): cv.string}


def _client(hass: HomeAssistant, call: ServiceCall) -> CaernApiClient:
    """Resolve o cliente: entrada informada, ou a única carregada."""
    entries: list[CaernConfigEntry] = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if getattr(e, "runtime_data", None)
    ]
    entry_id = call.data.get(ATTR_ENTRY)
    if entry_id:
        match = next((e for e in entries if e.entry_id == entry_id), None)
        if match is None:
            msg = f"config_entry_id {entry_id} não encontrado"
            raise ServiceValidationError(msg)
        return match.runtime_data.client
    if len(entries) != 1:
        msg = "Várias contas configuradas: informe config_entry_id"
        raise ServiceValidationError(msg)
    return entries[0].runtime_data.client


def async_setup_services(hass: HomeAssistant) -> None:
    """Registra os serviços do domínio (idempotente)."""
    if hass.services.has_service(DOMAIN, SERVICE_AUTOLEITURA):
        return

    async def _refresh() -> None:
        for entry in hass.config_entries.async_entries(DOMAIN):
            if getattr(entry, "runtime_data", None):
                await entry.runtime_data.async_request_refresh()

    async def autoleitura(call: ServiceCall) -> ServiceResponse:
        client = _client(hass, call)
        body = {
            "matricula": call.data[ATTR_MATRICULA],
            "leitura": call.data[ATTR_LEITURA],
        }
        try:
            result = await client.async_enviar_autoleitura(body)
        except CaernApiError as err:
            raise HomeAssistantError(str(err)) from err
        await _refresh()
        return {"resultado": result} if isinstance(result, (dict, list)) else {}

    async def add_imovel(call: ServiceCall) -> None:
        client = _client(hass, call)
        try:
            await client.async_adicionar_imovel(
                call.data[ATTR_MATRICULA], call.data[ATTR_CPF_CNPJ]
            )
        except CaernApiError as err:
            raise HomeAssistantError(str(err)) from err
        await _refresh()

    async def del_imovel(call: ServiceCall) -> None:
        client = _client(hass, call)
        try:
            await client.async_remover_imovel(call.data[ATTR_MATRICULA])
        except CaernApiError as err:
            raise HomeAssistantError(str(err)) from err
        await _refresh()

    async def segunda_via(call: ServiceCall) -> ServiceResponse:
        client = _client(hass, call)
        try:
            result = await client.async_segunda_via(call.data[ATTR_ID_CONTA])
        except CaernApiError as err:
            raise HomeAssistantError(str(err)) from err
        return {"segunda_via": result}

    reg = hass.services.async_register
    reg(
        DOMAIN,
        SERVICE_AUTOLEITURA,
        autoleitura,
        schema=vol.Schema(
            {
                **_ENTRY,
                vol.Required(ATTR_MATRICULA): cv.string,
                vol.Required(ATTR_LEITURA): vol.Coerce(int),
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    reg(
        DOMAIN,
        SERVICE_ADD_IMOVEL,
        add_imovel,
        schema=vol.Schema(
            {
                **_ENTRY,
                vol.Required(ATTR_MATRICULA): cv.string,
                vol.Required(ATTR_CPF_CNPJ): cv.string,
            }
        ),
    )
    reg(
        DOMAIN,
        SERVICE_DEL_IMOVEL,
        del_imovel,
        schema=vol.Schema({**_ENTRY, vol.Required(ATTR_MATRICULA): cv.string}),
    )
    reg(
        DOMAIN,
        SERVICE_SEGUNDA_VIA,
        segunda_via,
        schema=vol.Schema({**_ENTRY, vol.Required(ATTR_ID_CONTA): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
