import os

import pytest
from fastapi.testclient import TestClient

os.environ["APP_MODE"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["VECTOR_SEARCH_PROVIDER"] = "mock"

from ieum.providers.embedding.factory import get_embedding_provider
from ieum.providers.vector_search.factory import get_vector_search_provider
from main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_vector_store():
    get_vector_search_provider.cache_clear()
    get_embedding_provider.cache_clear()
    yield
    get_vector_search_provider.cache_clear()
    get_embedding_provider.cache_clear()


def _index_sample_chunks():
    response = client.post(
        "/api/v1/knowledge/chunks",
        json={
            "chunks": [
                {
                    "chunk_id": "marketing-1",
                    "document_id": "marketing",
                    "title": "마케팅 전략 회의",
                    "content": "마케팅 광고 예산은 삼천만 원으로 결정했습니다.",
                    "category": "history",
                    "chunk_index": 0,
                    "source_url": "mock://marketing",
                },
                {
                    "chunk_id": "infra-1",
                    "document_id": "infra",
                    "title": "인프라 회의",
                    "content": "서버 보안 패치는 다음 주에 적용합니다.",
                    "category": "reference",
                    "chunk_index": 0,
                    "source_url": "mock://infra",
                },
            ]
        },
    )
    assert response.status_code == 201
    assert response.json()["indexed_count"] == 2


def test_search_returns_grounded_source():
    _index_sample_chunks()

    response = client.post(
        "/api/v1/knowledge/search",
        json={
            "query": "마케팅 광고 예산",
            "top_k": 1,
            "min_score": 0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert len(body["hits"]) == 1
    assert body["hits"][0]["chunk_id"] == "marketing-1"
    assert body["hits"][0]["source_url"] == "mock://marketing"


def test_search_filters_category():
    _index_sample_chunks()

    response = client.post(
        "/api/v1/knowledge/search",
        json={
            "query": "서버 보안 패치",
            "category": "reference",
            "top_k": 3,
            "min_score": 0.1,
        },
    )

    assert response.status_code == 200
    assert {
        hit["category"] for hit in response.json()["hits"]
    } == {"reference"}


def test_search_without_sufficient_evidence_is_not_grounded():
    _index_sample_chunks()

    response = client.post(
        "/api/v1/knowledge/search",
        json={
            "query": "해외 출장 항공권 예약",
            "top_k": 3,
            "min_score": 0.99,
        },
    )

    assert response.status_code == 200
    assert response.json()["grounded"] is False
    assert response.json()["hits"] == []


def test_index_rejects_short_content():
    response = client.post(
        "/api/v1/knowledge/chunks",
        json={
            "chunks": [
                {
                    "chunk_id": "invalid",
                    "document_id": "invalid",
                    "title": "잘못된 문서",
                    "content": "짧음",
                    "chunk_index": 0,
                }
            ]
        },
    )

    assert response.status_code == 422
