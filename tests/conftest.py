"""Fixtures compartilhadas dos testes da CAERN."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.caern.const import DOMAIN

IMOVEL = {
    "matricula": 123456,
    "endereco": "Rua A, 1",
    "idMunicipio": 7,
    "situacaoAgua": "LIGADA",
    "situacaoEsgoto": "SEM REDE",
    "ocorrenciaOperacionalAtiva": None,
}
CONTAS = [
    {"id": 1, "anoMes": "202509", "paga": True, "valor": 50.0, "consumoMedido": 8},
    {"id": 2, "anoMes": "202510", "paga": False, "valor": 72.5, "consumoMedido": 11},
]
HISTORICO = [
    {"anoMes": 202509, "consumo": 8, "consumoMedio": 9},
    {"anoMes": 202510, "consumo": 11, "consumoMedio": 9},
]
QUANTIDADES = {"contas": 1, "imoveis": 1, "registrosAbertos": 0}
OCORRENCIAS = [
    {"idMunicipio": 7, "dataConclusao": None, "motivo": "Manutenção", "descricao": "x"}
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Habilita custom_components nos testes."""


@pytest.fixture
def mock_client() -> Generator[AsyncMock]:
    """Cliente CAERN falso com dados de um imóvel."""
    with (
        patch("custom_components.caern.CaernApiClient", autospec=True) as cls,
        patch("custom_components.caern.config_flow.CaernApiClient", new=cls),
    ):
        client = cls.return_value
        client.uid = "uid-1"
        client.async_login = AsyncMock()
        client.async_list_imoveis = AsyncMock(return_value=[IMOVEL])
        client.async_quantidades = AsyncMock(return_value=QUANTIDADES)
        client.async_ocorrencias_por_imovel = AsyncMock(return_value=OCORRENCIAS)
        client.async_list_contas = AsyncMock(return_value=CONTAS)
        client.async_historico_consumo = AsyncMock(return_value=HISTORICO)
        client.async_enviar_autoleitura = AsyncMock(return_value={"ok": True})
        client.async_adicionar_imovel = AsyncMock(return_value=None)
        client.async_remover_imovel = AsyncMock(return_value=None)
        client.async_segunda_via = AsyncMock(return_value="http://2via")
        yield client


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Config entry da CAERN."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="uid-1",
        title="CAERN (a@b.c)",
        data={"email": "a@b.c", "password": "secret"},
    )
