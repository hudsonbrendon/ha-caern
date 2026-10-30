"""Diagnóstico da integração CAERN (dados sensíveis redigidos)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import CaernConfigEntry

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "unique_id",
    "matricula",
    "inscricao",
    "endereco",
    "nome",
    "cpf",
    "cnpj",
    "cpfCnpj",
    "telefone",
    "codigoBarras",
    "qrCodePix",
    "linhaDigitavel",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CaernConfigEntry
) -> dict[str, Any]:
    """Retorna o config entry e o último snapshot do coordinator, redigidos."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    # ponytail: imóveis são indexados pela matrícula; vira lista pra não vazar a chave
    snapshot = {**data, "imoveis": list(data.get("imoveis", {}).values())}
    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "unique_id": entry.unique_id}, TO_REDACT
        ),
        "data": async_redact_data(snapshot, TO_REDACT),
    }
