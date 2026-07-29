import os
from functools import lru_cache

from ieum.providers.embedding.base import EmbeddingProvider
from ieum.providers.embedding.mock import MockEmbeddingProvider
from ieum.providers.embedding.nvidia import NvidiaEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockEmbeddingProvider()
    if provider == "nvidia":
        return NvidiaEmbeddingProvider()
    raise RuntimeError(f"지원하지 않는 EMBEDDING_PROVIDER입니다: {provider}")
