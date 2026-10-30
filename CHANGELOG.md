# Changelog

## Unreleased

## 0.1.1 - 2026-10-30

Modernization for Home Assistant 2026.10 / Python 3.14.

- Fix: `api.py` used `async_timeout`, which is no longer shipped with Home
  Assistant; switched to `asyncio.timeout`. Fix the `DeviceInfo` import path
  (`homeassistant.helpers.device_registry`). The integration failed to load
  on current HA without these.
- Fix: device name now includes the property address (the lookup read the
  wrong dict level, so the address was always dropped).
- `entry.runtime_data` is now the coordinator (`CaernConfigEntry =
  ConfigEntry[CaernDataUpdateCoordinator]`); `data.py` removed; coordinator
  receives the config entry explicitly.
- Services are registered once in `async_setup` (`async_setup_services`);
  dead `add_update_listener` removed (there is no options flow).
- Platforms use `AddConfigEntryEntitiesCallback` and declare
  `PARALLEL_UPDATES = 0`.
- New diagnostics (credentials, CPF/CNPJ, matrícula, address, barcode and PIX
  redacted) and `quality_scale.yaml`.
- Tooling: `pyproject.toml` (ruff, pytest), `requirements_test.txt`
  (pytest-homeassistant-custom-component 0.13.375), GitHub workflows (tests on
  Python 3.14, hassfest, HACS, release), HA integration tests, HACS floor
  `2025.6.0`.

## 0.1.0

First release.
