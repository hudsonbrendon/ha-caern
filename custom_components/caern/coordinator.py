"""Coordinator da CAERN: imóveis + contas + consumo + ocorrências."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CaernApiError, CaernAuthError
from .const import DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import CaernApiClient


def _matricula(imovel: dict[str, Any]) -> str:
    return str(imovel.get("matricula"))


class CaernDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Puxa imóveis e, por imóvel, contas/histórico/ocorrência."""

    def __init__(self, hass: HomeAssistant, client: CaernApiClient) -> None:
        """Inicializa o coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self.client = client

    def imovel(self, matricula: str) -> dict[str, Any] | None:
        """Retorna o imóvel pelo número de matrícula."""
        return (self.data or {}).get("imoveis", {}).get(matricula)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self._fetch_all()
        except CaernAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CaernApiError as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch_all(self) -> dict[str, Any]:
        imoveis_list = await self.client.async_list_imoveis()
        quantidades: dict[str, Any] = {}
        try:
            quantidades = await self.client.async_quantidades()
        except CaernApiError as err:
            LOGGER.debug("quantidades indisponível: %s", err)

        ocorrencias: list[dict[str, Any]] = []
        try:
            ocorrencias = await self.client.async_ocorrencias_por_imovel()
        except CaernApiError as err:
            LOGGER.debug("ocorrências indisponível: %s", err)

        imoveis: dict[str, dict[str, Any]] = {}
        for imv in imoveis_list:
            mat = _matricula(imv)
            contas, historico = await asyncio.gather(
                self.client.async_list_contas(mat),
                self.client.async_historico_consumo(mat),
                return_exceptions=True,
            )
            imoveis[mat] = {
                "imovel": imv,
                "contas": [] if isinstance(contas, Exception) else contas,
                "historico": [] if isinstance(historico, Exception) else historico,
            }
        return {
            "imoveis": imoveis,
            "quantidades": quantidades,
            "ocorrencias": ocorrencias,
        }
