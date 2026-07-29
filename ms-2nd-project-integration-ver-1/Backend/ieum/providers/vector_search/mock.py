import math

from ieum.providers.embedding.base import EmbeddingProvider
from ieum.providers.vector_search.base import VectorSearchProvider
from ieum.schemas.knowledge import DocumentChunkInput, KnowledgeSearchHit


class MockVectorSearchProvider(VectorSearchProvider):
    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider
        self._chunks: dict[str, tuple[DocumentChunkInput, list[float]]] = {}

    @property
    def provider_name(self) -> str:
        return "mock_vector_search"

    def index_chunks(self, chunks: list[DocumentChunkInput]) -> int:
        vectors = self.embedding_provider.embed_documents(
            [chunk.content for chunk in chunks]
        )
        for chunk, vector in zip(chunks, vectors, strict=True):
            self._chunks[chunk.chunk_id] = (chunk, vector)
        return len(chunks)

    def search(
        self,
        query: str,
        *,
        category: str | None,
        top_k: int,
        min_score: float,
    ) -> list[KnowledgeSearchHit]:
        query_vector = self.embedding_provider.embed_query(query)
        hits = []
        for chunk, vector in self._chunks.values():
            if category and chunk.category != category:
                continue
            score = self._cosine_similarity(query_vector, vector)
            if score < min_score:
                continue
            hits.append(
                KnowledgeSearchHit(
                    **chunk.model_dump(),
                    score=score,
                )
            )
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)
