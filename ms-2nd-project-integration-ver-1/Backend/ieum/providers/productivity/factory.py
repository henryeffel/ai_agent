import os
from functools import lru_cache

from ieum.providers.productivity.base import ProductivityProvider
from ieum.providers.productivity.mock import MockMicrosoft365Provider


@lru_cache
def get_productivity_provider() -> ProductivityProvider:
    provider = os.getenv("PRODUCTIVITY_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockMicrosoft365Provider()
    if provider == "logic_apps":
        from ieum.providers.productivity.logic_apps import (
            LogicAppsMicrosoft365Provider,
        )

        return LogicAppsMicrosoft365Provider()
    if provider == "microsoft_graph":
        from ieum.providers.productivity.graph import (
            MicrosoftGraphProductivityProvider,
        )
        from ieum.providers.productivity.graph_auth import (
            ClientCredentialsGraphTokenProvider,
            EnvironmentGraphTokenProvider,
        )

        auth_mode = os.getenv("GRAPH_AUTH_MODE", "delegated").lower()
        token_provider = (
            ClientCredentialsGraphTokenProvider()
            if auth_mode == "application"
            else EnvironmentGraphTokenProvider()
        )
        return MicrosoftGraphProductivityProvider(
            token_provider,
            auth_mode=auth_mode,
        )
    raise RuntimeError(
        f"지원하지 않는 PRODUCTIVITY_PROVIDER입니다: {provider}"
    )
