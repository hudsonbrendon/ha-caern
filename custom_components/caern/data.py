"""Tipos compartilhados da integração CAERN."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import CaernApiClient
    from .coordinator import CaernDataUpdateCoordinator


type CaernConfigEntry = ConfigEntry[CaernData]


@dataclass
class CaernData:
    """Dados guardados no ConfigEntry."""

    client: CaernApiClient
    coordinator: CaernDataUpdateCoordinator
    integration: Integration
