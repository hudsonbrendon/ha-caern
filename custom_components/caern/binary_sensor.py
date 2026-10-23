"""Binary sensor da CAERN: ocorrência operacional ativa (falta d'água/obra)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .entity import CaernImovelEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import CaernDataUpdateCoordinator
    from .data import CaernConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CaernConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cria o binary sensor de ocorrência por imóvel."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CaernOcorrenciaSensor(coordinator, matricula)
        for matricula in (coordinator.data or {}).get("imoveis", {})
    )


class CaernOcorrenciaSensor(CaernImovelEntity, BinarySensorEntity):
    """Ligado quando há falta d'água/obra ativa afetando o imóvel."""

    _attr_translation_key = "ocorrencia"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: CaernDataUpdateCoordinator, matricula: str) -> None:
        """Inicializa o binary sensor."""
        super().__init__(coordinator, matricula)
        self._attr_unique_id = f"{matricula}_ocorrencia"

    def _ocorrencia(self) -> dict[str, Any] | None:
        node = (self.coordinator.data or {}).get("imoveis", {}).get(self._matricula, {})
        imovel = node.get("imovel") or {}
        ativa = imovel.get("ocorrenciaOperacionalAtiva")
        if ativa:
            return ativa
        # Fallback: casa com a lista global por município/bairro do imóvel.
        for oc in (self.coordinator.data or {}).get("ocorrencias", []):
            if oc.get("idMunicipio") == imovel.get("idMunicipio") and oc.get(
                "dataConclusao"
            ) in (None, ""):
                return oc
        return None

    @property
    def is_on(self) -> bool:
        """True se há ocorrência ativa."""
        return self._ocorrencia() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Detalhes da ocorrência ativa."""
        oc = self._ocorrencia() or {}
        return {
            "motivo": oc.get("motivo"),
            "descricao": oc.get("descricao"),
            "areas_afetadas": oc.get("areasAfetadas") or oc.get("textoAreasAfetadas"),
            "abertura": oc.get("dataAbertura"),
            "previsao_normalizacao": oc.get("dataPrevisaoNormalizacao")
            or oc.get("dataPrevisao"),
        }
