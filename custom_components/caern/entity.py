"""Entidade base da CAERN."""

from __future__ import annotations

from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CaernDataUpdateCoordinator


class CaernImovelEntity(CoordinatorEntity[CaernDataUpdateCoordinator]):
    """Base por imóvel (device = matrícula)."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: CaernDataUpdateCoordinator, matricula: str
    ) -> None:
        """matricula identifica o imóvel."""
        super().__init__(coordinator)
        self._matricula = matricula
        endereco = (coordinator.imovel(matricula) or {}).get("endereco")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, matricula)},
            manufacturer="CAERN",
            model="Imóvel",
            name=f"CAERN {matricula}" + (f" — {endereco}" if endereco else ""),
        )
