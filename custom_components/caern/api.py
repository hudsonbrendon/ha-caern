"""Cliente da API da CAERN (engenharia reversa do app br.com.caern.mobile.caernmobile).

O app autentica no **Firebase Auth** (e-mail/senha, ou Google/Facebook) e usa o
**ID token** do Firebase como header `Authorization` (valor cru, sem "Bearer")
contra `https://servermobile.caern.com.br/rest/`. Toda resposta é embrulhada em
`Response<T> = {status, message, type, content}`.

Esta integração replica o login por **e-mail/senha** via Firebase REST
(identitytoolkit + securetoken) — contas criadas com Google/Facebook não têm
senha e não funcionam aqui.

Chave Firebase do projeto `caernmobile` extraída do APK (google_api_key).
"""

from __future__ import annotations

import socket
import time
from typing import Any

import aiohttp
import async_timeout

BASE_URL = "https://servermobile.caern.com.br/rest"
FIREBASE_API_KEY = "AIzaSyCeahuUfDsqsCcaiPTv4Gf0WTEuJjg0cgo"
_SIGNIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"

_TIMEOUT = 90  # o app usa 90s de read/connect timeout
_REFRESH_SKEW = 60  # renova o token 60s antes de expirar


class CaernApiError(Exception):
    """Erro geral da API."""


class CaernApiCommunicationError(CaernApiError):
    """Falha de comunicação/timeout."""


class CaernAuthError(CaernApiError):
    """Credenciais inválidas ou sessão expirada."""


class CaernApiClient:
    """Cliente autenticado da CAERN (Firebase ID token como Authorization)."""

    def __init__(self, email: str, password: str, session: aiohttp.ClientSession) -> None:
        """email/password = login Firebase (e-mail/senha) do app CAERN."""
        self._email = email
        self._password = password
        self._session = session
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0
        self.uid: str | None = None

    # --- Firebase Auth ---

    async def async_login(self) -> None:
        """Faz signInWithPassword e guarda os tokens."""
        data = await self._firebase(
            _SIGNIN_URL,
            {
                "email": self._email,
                "password": self._password,
                "returnSecureToken": True,
            },
        )
        self._id_token = data["idToken"]
        self._refresh_token = data["refreshToken"]
        self._expires_at = time.monotonic() + int(data.get("expiresIn", 3600))
        self.uid = data.get("localId")

    async def _refresh(self) -> None:
        data = await self._firebase(
            _REFRESH_URL,
            {"grant_type": "refresh_token", "refresh_token": self._refresh_token},
        )
        self._id_token = data["id_token"]
        self._refresh_token = data["refresh_token"]
        self._expires_at = time.monotonic() + int(data.get("expires_in", 3600))

    async def _firebase(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with async_timeout.timeout(_TIMEOUT):
                resp = await self._session.post(
                    url, params={"key": FIREBASE_API_KEY}, json=payload
                )
                body = await resp.json()
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            msg = f"erro de comunicação com o Firebase: {err}"
            raise CaernApiCommunicationError(msg) from err
        if resp.status >= 400:
            reason = (body.get("error") or {}).get("message", f"HTTP {resp.status}")
            if reason in ("EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"):
                msg = "e-mail ou senha inválidos"
                raise CaernAuthError(msg)
            msg = f"Firebase recusou: {reason}"
            raise CaernAuthError(msg)
        return body

    async def _token(self) -> str:
        if self._id_token is None:
            await self.async_login()
        elif time.monotonic() >= self._expires_at - _REFRESH_SKEW:
            await self._refresh()
        return self._id_token  # type: ignore[return-value]

    # --- CAERN REST ---

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Chama o backend e devolve o campo `content` do Response<T>."""
        token = await self._token()
        url = f"{BASE_URL}/{path}"
        try:
            async with async_timeout.timeout(_TIMEOUT):
                resp = await self._session.request(
                    method,
                    url,
                    headers={"Authorization": token, "Accept": "application/json"},
                    params=params,
                    json=json,
                )
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            msg = f"erro de comunicação com a CAERN: {err}"
            raise CaernApiCommunicationError(msg) from err
        if resp.status in (401, 403):
            msg = "token recusado pela CAERN (401/403)"
            raise CaernAuthError(msg)
        if resp.status >= 400:
            text = await resp.text()
            msg = f"CAERN respondeu {resp.status}: {text[:200]}"
            raise CaernApiError(msg)
        if resp.content_type == "application/json":
            body = await resp.json()
            if isinstance(body, dict) and "content" in body:
                return body["content"]
            return body
        return await resp.text()

    # --- leituras ---

    async def async_list_imoveis(self) -> list[dict[str, Any]]:
        """GET imovel -> imóveis (matrículas) do usuário."""
        return await self._request("GET", "imovel") or []

    async def async_get_imovel(self, matricula: str | int) -> dict[str, Any]:
        """GET imovel/{matricula} -> detalhe do imóvel."""
        return await self._request("GET", f"imovel/{matricula}")

    async def async_list_contas(
        self, matricula: str | int, incluir_pagas_30_dias: bool = True
    ) -> list[dict[str, Any]]:
        """GET conta?matricula= -> contas (abertas + pagas recentes)."""
        return (
            await self._request(
                "GET",
                "conta",
                params={
                    "matricula": str(matricula),
                    "incluir_pagas_30_dias": str(incluir_pagas_30_dias).lower(),
                },
            )
            or []
        )

    async def async_get_conta(self, id_conta: str | int) -> dict[str, Any]:
        """GET conta/{idConta} -> detalhe da conta (com qrCodePix, código de barras)."""
        return await self._request("GET", f"conta/{id_conta}")

    async def async_list_contas_pagas(
        self, matricula: str | int, ano: int
    ) -> list[dict[str, Any]]:
        """GET contas_pagas?matricula=&ano= -> contas pagas do ano."""
        return (
            await self._request(
                "GET",
                "contas_pagas",
                params={"matricula": str(matricula), "ano": ano},
            )
            or []
        )

    async def async_historico_consumo(
        self, matricula: str | int
    ) -> list[dict[str, Any]]:
        """GET historicoconsumo/{matricula} -> histórico de consumo (m³)."""
        return await self._request("GET", f"historicoconsumo/{matricula}") or []

    async def async_quantidades(self) -> dict[str, Any]:
        """GET quantidades -> resumo (contas abertas, imóveis, registros abertos)."""
        return await self._request("GET", "quantidades") or {}

    async def async_ocorrencias_por_imovel(self) -> list[dict[str, Any]]:
        """GET ocorrencia_operacional_por_imovel/todos -> faltas d'água/obras ativas."""
        return (
            await self._request("GET", "ocorrencia_operacional_por_imovel/todos") or []
        )

    async def async_segunda_via(self, id_conta: str | int) -> Any:
        """GET segundavia/{idConta} -> 2ª via (link/base64)."""
        return await self._request("GET", f"segundavia/{id_conta}")

    async def async_listar_debitos(self, matricula: str | int) -> Any:
        """GET v2/listar_debitos -> débitos do imóvel."""
        return await self._request(
            "GET", "v2/listar_debitos", params={"matricula": str(matricula)}
        )

    # --- ações ---

    async def async_adicionar_imovel(self, matricula: str, cpf_cnpj: str) -> Any:
        """PUT imovel/{matricula}?cpfCnpj= -> vincula um imóvel à conta."""
        return await self._request(
            "PUT", f"imovel/{matricula}", params={"cpfCnpj": cpf_cnpj}
        )

    async def async_remover_imovel(self, matricula: str) -> Any:
        """DELETE imovel/{matricula} -> desvincula o imóvel."""
        return await self._request("DELETE", f"imovel/{matricula}")

    async def async_enviar_autoleitura(self, body: dict[str, Any]) -> Any:
        """POST autoleitura/envio -> envia a autoleitura do hidrômetro."""
        return await self._request("POST", "autoleitura/envio", json=body)
