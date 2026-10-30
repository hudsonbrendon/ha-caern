"""Setup, entidades, serviços, diagnóstico e config flow da CAERN."""

from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.caern.api import CaernAuthError
from custom_components.caern.const import DOMAIN
from custom_components.caern.diagnostics import async_get_config_entry_diagnostics


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_setup_entities_and_unload(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)

    assert hass.states.get("sensor.caern_123456_rua_a_1_current_bill").state == "72.5"
    assert (
        hass.states.get("sensor.caern_123456_rua_a_1_metered_consumption").state == "11"
    )
    assert (
        hass.states.get("sensor.caern_123456_rua_a_1_consumption_history").state == "11"
    )
    assert hass.states.get("sensor.caern_123456_rua_a_1_status").state == "LIGADA"
    assert hass.states.get("sensor.open_bills").state == "1"
    assert (
        hass.states.get("binary_sensor.caern_123456_rua_a_1_outage_water_issue").state
        == "on"
    )

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "123456"), config_entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "CAERN"

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_services(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)

    resp = await hass.services.async_call(
        DOMAIN,
        "enviar_autoleitura",
        {"matricula": "123456", "leitura": 1234},
        blocking=True,
        return_response=True,
    )
    assert resp == {"resultado": {"ok": True}}
    mock_client.async_enviar_autoleitura.assert_awaited_once_with(
        {"matricula": "123456", "leitura": 1234}
    )

    resp = await hass.services.async_call(
        DOMAIN, "segunda_via", {"id_conta": "2"}, blocking=True, return_response=True
    )
    assert resp == {"segunda_via": "http://2via"}

    await hass.services.async_call(
        DOMAIN, "adicionar_imovel", {"matricula": "9", "cpf_cnpj": "1"}, blocking=True
    )
    mock_client.async_adicionar_imovel.assert_awaited_once_with("9", "1")
    await hass.services.async_call(
        DOMAIN, "remover_imovel", {"matricula": "9"}, blocking=True
    )
    mock_client.async_remover_imovel.assert_awaited_once_with("9")


async def test_diagnostics_redacts(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diag["entry"]["data"]["password"] == "**REDACTED**"
    assert diag["entry"]["data"]["email"] == "**REDACTED**"
    imovel = diag["data"]["imoveis"][0]["imovel"]
    assert imovel["matricula"] == "**REDACTED**"
    assert imovel["endereco"] == "**REDACTED**"
    assert "secret" not in str(diag)


async def test_config_flow(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    mock_client.async_login.side_effect = CaernAuthError("x")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "A@b.c", "password": "p"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_client.async_login.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "A@b.c", "password": "p"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"email": "a@b.c", "password": "p"}
    assert result["result"].unique_id == "uid-1"
