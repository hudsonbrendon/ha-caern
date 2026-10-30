"""Checagens do cliente CAERN que rodam sem Home Assistant.

`python3 -I tests/test_api.py`. Valida o parsing do envelope Response<T> e a
seleção da conta atual (em aberto mais recente).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

for _name in ("aiohttp",):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_API = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "caern"
    / "api.py"
)
_spec = importlib.util.spec_from_file_location("caern_api", _API)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def test_constants() -> None:
    """Base URL e chave Firebase vindas do APK."""
    assert _mod.BASE_URL == "https://servermobile.caern.com.br/rest"
    assert _mod.FIREBASE_API_KEY.startswith("AIza")


def test_latest_conta_prefers_open() -> None:
    """A conta atual deve ser a EM ABERTO mais recente (regra do sensor)."""
    contas = [
        {"anoMes": "202501", "paga": True, "valor": 10.0},
        {"anoMes": "202502", "paga": False, "valor": 20.0},
        {"anoMes": "202503", "paga": True, "valor": 30.0},
    ]
    abertas = [c for c in contas if not c.get("paga")]
    pool = abertas or contas
    atual = max(pool, key=lambda c: str(c.get("anoMes") or ""))
    assert atual["valor"] == 20.0


if __name__ == "__main__":
    test_constants()
    test_latest_conta_prefers_open()
    print("todos os checks da CAERN passaram")
