"""Sensores da CAERN (por imóvel + resumo da conta)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    """Cria sensores por imóvel + resumo global."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        CaernContasAbertasSensor(coordinator),
        CaernImoveisSensor(coordinator),
        CaernRegistrosAbertosSensor(coordinator),
    ]
    for matricula in (coordinator.data or {}).get("imoveis", {}):
        entities.extend(
            [
                CaernContaSensor(coordinator, matricula),
                CaernConsumoSensor(coordinator, matricula),
                CaernConsumoHistoricoSensor(coordinator, matricula),
                CaernSituacaoSensor(coordinator, matricula),
            ]
        )
    async_add_entities(entities)


def _latest_conta(contas: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Conta em aberto mais recente; senão a mais recente por anoMes."""
    if not contas:
        return None
    abertas = [c for c in contas if not c.get("paga")]
    pool = abertas or contas
    return max(pool, key=lambda c: str(c.get("anoMes") or ""))


class CaernContaSensor(CaernImovelEntity, SensorEntity):
    """Valor da conta atual (em aberto, senão a última)."""

    _attr_translation_key = "conta"
    _attr_native_unit_of_measurement = "BRL"

    def __init__(self, coordinator: CaernDataUpdateCoordinator, matricula: str) -> None:
        """Inicializa o sensor de conta."""
        super().__init__(coordinator, matricula)
        self._attr_unique_id = f"{matricula}_conta"

    def _conta(self) -> dict[str, Any] | None:
        node = (self.coordinator.data or {}).get("imoveis", {}).get(self._matricula, {})
        return _latest_conta(node.get("contas") or [])

    @property
    def native_value(self) -> float | None:
        """Valor em reais."""
        conta = self._conta()
        return conta.get("valor") if conta else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Vencimento, situação, código de barras, PIX etc."""
        conta = self._conta() or {}
        return {
            "id_conta": conta.get("id"),
            "ano_mes": conta.get("anoMes"),
            "vencimento": conta.get("dataVencimento"),
            "situacao": conta.get("situacao"),
            "paga": conta.get("paga"),
            "data_pagamento": conta.get("dataPagamento"),
            "valor_agua": conta.get("valorAgua"),
            "valor_esgoto": conta.get("valorEsgoto"),
            "codigo_barras": conta.get("codigoBarras"),
            "pix_copia_cola": conta.get("qrCodePix"),
        }


class CaernConsumoSensor(CaernImovelEntity, SensorEntity):
    """Consumo medido na conta atual (m³)."""

    _attr_translation_key = "consumo"
    _attr_native_unit_of_measurement = "m³"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CaernDataUpdateCoordinator, matricula: str) -> None:
        """Inicializa o sensor de consumo."""
        super().__init__(coordinator, matricula)
        self._attr_unique_id = f"{matricula}_consumo"

    def _conta(self) -> dict[str, Any] | None:
        node = (self.coordinator.data or {}).get("imoveis", {}).get(self._matricula, {})
        return _latest_conta(node.get("contas") or [])

    @property
    def native_value(self) -> int | None:
        """Consumo medido em m³."""
        conta = self._conta()
        return conta.get("consumoMedido") if conta else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Faturado, média, leituras."""
        conta = self._conta() or {}
        return {
            "consumo_faturado": conta.get("consumoFaturado"),
            "media_mes": conta.get("mediaMes"),
            "leitura_atual": conta.get("leituraAtual"),
            "leitura_anterior": conta.get("leituraAnterior"),
            "data_leitura_atual": conta.get("dataLeituraAtual"),
            "dias_consumo": conta.get("diasConsumo"),
        }


class CaernConsumoHistoricoSensor(CaernImovelEntity, SensorEntity):
    """Consumo do mês mais recente no histórico (m³)."""

    _attr_translation_key = "consumo_historico"
    _attr_native_unit_of_measurement = "m³"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CaernDataUpdateCoordinator, matricula: str) -> None:
        """Inicializa o sensor de histórico de consumo."""
        super().__init__(coordinator, matricula)
        self._attr_unique_id = f"{matricula}_consumo_historico"

    def _historico(self) -> list[dict[str, Any]]:
        node = (self.coordinator.data or {}).get("imoveis", {}).get(self._matricula, {})
        return node.get("historico") or []

    @property
    def native_value(self) -> int | None:
        """Consumo do último mês do histórico."""
        hist = self._historico()
        if not hist:
            return None
        return max(hist, key=lambda h: h.get("anoMes", 0)).get("consumo")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Série completa do histórico (anoMes -> consumo)."""
        return {
            "historico": [
                {
                    "ano_mes": h.get("anoMes"),
                    "consumo": h.get("consumo"),
                    "consumo_medio": h.get("consumoMedio"),
                }
                for h in sorted(self._historico(), key=lambda h: h.get("anoMes", 0))
            ]
        }


class CaernSituacaoSensor(CaernImovelEntity, SensorEntity):
    """Situação de água/esgoto do imóvel."""

    _attr_translation_key = "situacao"

    def __init__(self, coordinator: CaernDataUpdateCoordinator, matricula: str) -> None:
        """Inicializa o sensor de situação."""
        super().__init__(coordinator, matricula)
        self._attr_unique_id = f"{matricula}_situacao"

    def _imovel(self) -> dict[str, Any]:
        node = (self.coordinator.data or {}).get("imoveis", {}).get(self._matricula, {})
        return node.get("imovel") or {}

    @property
    def native_value(self) -> str | None:
        """Situação da água."""
        return self._imovel().get("situacaoAgua")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Esgoto, endereço, autoleitura."""
        imovel = self._imovel()
        return {
            "situacao_esgoto": imovel.get("situacaoEsgoto"),
            "endereco": imovel.get("endereco"),
            "inscricao": imovel.get("inscricao"),
            "autoleitura_habilitada": imovel.get("autoLeitura"),
            "autoleitura_inicio": imovel.get("autoLeituraInicio"),
            "autoleitura_fim": imovel.get("autoLeituraFim"),
        }


class _ResumoSensor(CoordinatorEntity["CaernDataUpdateCoordinator"], SensorEntity):
    """Sensor global (resumo da conta do usuário)."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CaernDataUpdateCoordinator, key: str) -> None:
        """key = campo de `quantidades`."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"caern_{key}"
        self._attr_translation_key = key

    @property
    def native_value(self) -> int | None:
        """Valor do campo em `quantidades`."""
        return (self.coordinator.data or {}).get("quantidades", {}).get(self._key)


class CaernContasAbertasSensor(_ResumoSensor):
    """Total de contas em aberto."""

    def __init__(self, coordinator: CaernDataUpdateCoordinator) -> None:
        """Inicializa."""
        super().__init__(coordinator, "contas")


class CaernImoveisSensor(_ResumoSensor):
    """Total de imóveis vinculados."""

    def __init__(self, coordinator: CaernDataUpdateCoordinator) -> None:
        """Inicializa."""
        super().__init__(coordinator, "imoveis")


class CaernRegistrosAbertosSensor(_ResumoSensor):
    """Total de registros/atendimentos abertos."""

    def __init__(self, coordinator: CaernDataUpdateCoordinator) -> None:
        """Inicializa."""
        super().__init__(coordinator, "registrosAbertos")
