import os
from functools import lru_cache

from ieum.providers.llm.base import LLMProvider
from ieum.providers.llm.mock import MockLLMProvider
from ieum.providers.llm.nvidia import NvidiaLLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockLLMProvider()
    if provider == "nvidia":
        return NvidiaLLMProvider()
    raise RuntimeError(f"지원하지 않는 LLM_PROVIDER입니다: {provider}")
