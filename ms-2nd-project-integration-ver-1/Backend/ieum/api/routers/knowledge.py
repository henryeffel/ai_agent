from fastapi import APIRouter

from ieum.api.errors import ApiException
from ieum.config import get_settings
from ieum.providers.vector_search import get_vector_search_provider
from ieum.schemas.knowledge import (
    ChunkIndexRequest,
    ChunkIndexResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)


router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/chunks", response_model=ChunkIndexResponse, status_code=201)
def index_knowledge_chunks(request: ChunkIndexRequest):
    if get_settings().app_mode == "demo":
        raise ApiException(
            403,
            "demo_write_disabled",
            "공개 데모에서는 Knowledge 색인 API를 사용할 수 없습니다.",
        )
    provider = get_vector_search_provider()
    return ChunkIndexResponse(
        indexed_count=provider.index_chunks(request.chunks),
        provider=provider.provider_name,
    )


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(request: KnowledgeSearchRequest):
    provider = get_vector_search_provider()
    hits = provider.search(
        request.query,
        category=request.category,
        top_k=request.top_k,
        min_score=request.min_score,
    )
    return KnowledgeSearchResponse(
        provider=provider.provider_name,
        grounded=bool(hits),
        hits=hits,
    )
