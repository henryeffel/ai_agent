import os
import threading
import time
from abc import ABC, abstractmethod

import httpx

from ieum.providers.productivity.base import (
    ProductivityConfigurationError,
    ProductivityProviderError,
    ProductivityTimeoutError,
    ProductivityUnauthorizedError,
)


class GraphTokenProvider(ABC):
    @abstractmethod
    def get_access_token(self) -> str:
        """Return a non-empty access token, refreshing it when necessary."""


class EnvironmentGraphTokenProvider(GraphTokenProvider):
    def get_access_token(self) -> str:
        token = os.getenv("GRAPH_ACCESS_TOKEN", "").strip()
        if not token:
            raise ProductivityConfigurationError(
                "GRAPH_ACCESS_TOKEN이 설정되지 않았습니다."
            )
        return token


class ClientCredentialsGraphTokenProvider(GraphTokenProvider):
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(
            timeout=float(os.getenv("PRODUCTIVITY_TIMEOUT_SECONDS", "10"))
        )
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get_access_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._expires_at - 60:
                return self._token
            tenant_id = _required("GRAPH_TENANT_ID")
            client_id = _required("GRAPH_CLIENT_ID")
            client_secret = _required("GRAPH_CLIENT_SECRET")
            url = (
                "https://login.microsoftonline.com/"
                f"{tenant_id}/oauth2/v2.0/token"
            )
            try:
                response = self._client.post(
                    url,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": "https://graph.microsoft.com/.default",
                        "grant_type": "client_credentials",
                    },
                )
            except httpx.TimeoutException as exc:
                raise ProductivityTimeoutError() from exc
            except httpx.RequestError as exc:
                raise ProductivityProviderError(
                    "network_error", "Entra ID token 요청에 실패했습니다."
                ) from exc
            if response.status_code in {400, 401}:
                raise ProductivityUnauthorizedError()
            if response.status_code >= 400:
                raise ProductivityProviderError(
                    "token_upstream_error", "Entra ID token 발급에 실패했습니다."
                )
            try:
                data = response.json()
                token = data["access_token"]
                expires_in = int(data.get("expires_in", 3600))
            except (ValueError, KeyError, TypeError) as exc:
                raise ProductivityProviderError(
                    "invalid_token_response",
                    "Entra ID token 응답 형식이 올바르지 않습니다.",
                ) from exc
            self._token = token
            self._expires_at = time.time() + max(1, expires_in)
            return token


def _required(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise ProductivityConfigurationError(f"{key}가 설정되지 않았습니다.")
    return value
