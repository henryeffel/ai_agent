from abc import ABC, abstractmethod

from ieum.schemas.knowledge import DocumentChunkInput, KnowledgeSearchHit


class VectorSearchProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a stable provider identifier."""

    @abstractmethod
    def index_chunks(self, chunks: list[DocumentChunkInput]) -> int:
        """Index or update document chunks."""

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        category: str | None,
        top_k: int,
        min_score: float,
    ) -> list[KnowledgeSearchHit]:
        """Return relevant chunks ordered by similarity."""
