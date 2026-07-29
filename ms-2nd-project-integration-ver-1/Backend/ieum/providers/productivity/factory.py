import os
from functools import lru_cache

from ieum.providers.productivity.base import ProductivityProvider
from ieum.providers.productivity.mock import MockMicrosoft365Provider


@lru_cache
def get_productivity_provider() -> ProductivityProvider:
    provider = os.getenv("PRODUCTIVITY_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockMicrosoft365Provider()
    raise RuntimeError(
        f"지원하지 않는 PRODUCTIVITY_PROVIDER입니다: {provider}"
    )
