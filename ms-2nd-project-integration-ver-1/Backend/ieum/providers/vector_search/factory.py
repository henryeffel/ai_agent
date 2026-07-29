import os
from functools import lru_cache

from ieum.providers.embedding import get_embedding_provider
from ieum.providers.vector_search.base import VectorSearchProvider
from ieum.providers.vector_search.mock import MockVectorSearchProvider
from ieum.providers.vector_search.pgvector import PgVectorSearchProvider


@lru_cache
def get_vector_search_provider() -> VectorSearchProvider:
    provider = os.getenv("VECTOR_SEARCH_PROVIDER", "mock").lower()
    embedding_provider = get_embedding_provider()
    if provider == "mock":
        return MockVectorSearchProvider(embedding_provider)
    if provider == "pgvector":
        return PgVectorSearchProvider(embedding_provider)
    raise RuntimeError(
        f"지원하지 않는 VECTOR_SEARCH_PROVIDER입니다: {provider}"
    )
