import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

os.environ["APP_MODE"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["VECTOR_SEARCH_PROVIDER"] = "mock"
os.environ["PRODUCTIVITY_PROVIDER"] = "mock"

from ieum.database import get_engine, get_session_factory
from ieum.providers.embedding.factory import get_embedding_provider
from ieum.providers.llm.factory import get_llm_provider
from ieum.providers.vector_search.factory import get_vector_search_provider
from ieum.services.action_workflow import get_action_workflow_service
from main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_dependencies(tmp_path, monkeypatch):
    database_path = tmp_path / "grounded-workflow.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")

    get_action_workflow_service.cache_clear()
    get_vector_search_provider.cache_clear()
    get_embedding_provider.cache_clear()
    get_llm_provider.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()

    command.upgrade(Config("alembic.ini"), "head")

    yield

    get_action_workflow_service.cache_clear()
    get_vector_search_provider.cache_clear()
    get_embedding_provider.cache_clear()
    get_llm_provider.cache_clear()
    engine = get_engine()
    engine.dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()


def _index_marketing_evidence():
    response = client.post(
        "/api/v1/knowledge/chunks",
        json={
            "chunks": [
                {
                    "chunk_id": "marketing-budget-1",
                    "document_id": "marketing-policy",
                    "title": "마케팅 예산 승인 회의",
                    "content": (
                        "신제품 마케팅 광고 예산을 검토하고 후속 작업을 "
                        "할 일 목록으로 관리합니다."
                    ),
                    "category": "history",
                    "chunk_index": 0,
                    "source_url": "mock://marketing-budget",
                }
            ]
        },
    )
    assert response.status_code == 201


def test_grounded_plan_stores_evidence_chunk_ids():
    _index_marketing_evidence()

    response = client.post(
        "/api/v1/action-plans/grounded",
        json={
            "meeting_id": "meeting-grounded-1",
            "transcript": (
                "신제품 마케팅 광고 예산을 검토했고 후속 작업을 "
                "할 일 목록으로 관리하기로 했습니다."
            ),
            "category": "history",
            "top_k": 3,
            "min_score": 0.1,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert body["evidence_chunk_ids"] == ["marketing-budget-1"]
    assert body["evidence"] == [
        {
            "chunk_id": "marketing-budget-1",
            "document_id": "marketing-policy",
            "title": "마케팅 예산 승인 회의",
            "category": "history",
            "source": "mock://marketing-budget",
            "excerpt": "신제품 마케팅 광고 예산을 검토하고 후속 작업을 할 일 목록으로 관리합니다.",
            "similarity_score": body["evidence"][0]["similarity_score"],
        }
    ]
    assert body["evidence"][0]["similarity_score"] > 0.1
    assert body["actions"]
    assert body["actions"][0]["tool"] == "todo"

    stored = client.get(f"/api/v1/action-plans/{body['id']}")
    assert stored.status_code == 200
    assert stored.json()["evidence_chunk_ids"] == ["marketing-budget-1"]
    assert stored.json()["evidence"] == body["evidence"]


def test_grounded_plan_rejects_when_evidence_is_insufficient():
    _index_marketing_evidence()

    response = client.post(
        "/api/v1/action-plans/grounded",
        json={
            "meeting_id": "meeting-ungrounded-1",
            "transcript": (
                "해외 출장 항공권 예약과 현지 호텔 결제를 "
                "즉시 진행하기로 했습니다."
            ),
            "top_k": 3,
            "min_score": 0.99,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_evidence"
    assert "근거가 부족" in response.json()["error"]["message"]
