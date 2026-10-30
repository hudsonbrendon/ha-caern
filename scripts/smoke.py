"""Smoke test de terminal do cliente CAERN (sem Home Assistant).

Loga via Firebase (e-mail/senha) e despeja imóveis + contas + histórico, para
validar os campos antes de instalar no HA. Credenciais ficam só na sua máquina.

    pip install aiohttp
    CAERN_EMAIL=voce@email.com CAERN_PASSWORD='senha' python3 scripts/smoke.py
"""

from __future__ import annotations

import asyncio
import getpass
import importlib.util
import json
import os
import pathlib

import aiohttp

_API = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "caern"
    / "api.py"
)
_spec = importlib.util.spec_from_file_location("caern_api", _API)
_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_api)


async def main() -> None:
    """Loga e imprime imóveis, contas e consumo."""
    email = os.environ.get("CAERN_EMAIL") or input("E-mail CAERN: ")
    password = os.environ.get("CAERN_PASSWORD") or getpass.getpass("Senha: ")

    async with aiohttp.ClientSession() as session:
        client = _api.CaernApiClient(email=email, password=password, session=session)
        print("Logando no Firebase...")
        await client.async_login()
        print(f"OK. uid={client.uid}\n")

        imoveis = await client.async_list_imoveis()
        print(f"===== imóveis ({len(imoveis)}) =====")
        print(json.dumps(imoveis, indent=2, ensure_ascii=False))

        for imv in imoveis:
            mat = imv.get("matricula")
            print(f"\n===== conta(s) matrícula {mat} =====")
            print(
                json.dumps(
                    await client.async_list_contas(mat), indent=2, ensure_ascii=False
                )
            )
            print(f"----- histórico {mat} -----")
            print(
                json.dumps(
                    await client.async_historico_consumo(mat),
                    indent=2,
                    ensure_ascii=False,
                )
            )

        print("\n===== quantidades =====")
        print(
            json.dumps(await client.async_quantidades(), indent=2, ensure_ascii=False)
        )


if __name__ == "__main__":
    asyncio.run(main())
