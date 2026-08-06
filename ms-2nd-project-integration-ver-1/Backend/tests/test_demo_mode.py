import os
import subprocess
import sys

from fastapi.testclient import TestClient

from ieum.security.dependencies import get_actor_context
from main import app


client = TestClient(app)


def _demo_environment():
    environment = os.environ.copy()
    environment.update(
        {
            "APP_MODE": "demo",
            "LLM_PROVIDER": "nvidia",
            "EMBEDDING_PROVIDER": "nvidia",
            "VECTOR_SEARCH_PROVIDER": "pgvector",
            "PRODUCTIVITY_PROVIDER": "mock",
            "DATABASE_URL": "postgresql+psycopg://demo:demo@localhost/demo",
        }
    )
    return environment


def test_demo_mode_starts_without_registering_legacy_routes():
    code = """
import main
paths = set(main.app.openapi()['paths'])
legacy = {'/files', '/upload', '/chat', '/delete', '/execute-action'}
assert paths.isdisjoint(legacy)
assert '/api/v1/action-plans/{plan_id}/execute' in paths
assert 'ieum.api.routers.legacy_azure' not in __import__('sys').modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=_demo_environment(),
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_demo_mode_rejects_real_productivity_provider():
    environment = _demo_environment()
    environment["PRODUCTIVITY_PROVIDER"] = "microsoft_graph"
    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode != 0
    assert "안전한 공개 배포 Provider 조합" in result.stderr


def test_demo_mode_requires_postgresql():
    environment = _demo_environment()
    environment["DATABASE_URL"] = "sqlite:///demo.db"
    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode != 0
    assert "PostgreSQL DATABASE_URL" in result.stderr


def test_demo_identity_ignores_user_controlled_headers(monkeypatch):
    for key, value in _demo_environment().items():
        if key in {
            "APP_MODE",
            "LLM_PROVIDER",
            "EMBEDDING_PROVIDER",
            "VECTOR_SEARCH_PROVIDER",
            "PRODUCTIVITY_PROVIDER",
            "DATABASE_URL",
        }:
            monkeypatch.setenv(key, value)

    actor = get_actor_context(
        subject_id="forged-user",
        email="attacker@example.com",
        roles="viewer",
    )

    assert actor.subject_id == "public-demo-user"
    assert str(actor.email) == "demo.user@example.com"
    assert actor.roles == {"approver", "executor"}


def test_demo_mode_blocks_public_knowledge_index(monkeypatch):
    for key, value in _demo_environment().items():
        if key in {
            "APP_MODE",
            "LLM_PROVIDER",
            "EMBEDDING_PROVIDER",
            "VECTOR_SEARCH_PROVIDER",
            "PRODUCTIVITY_PROVIDER",
            "DATABASE_URL",
        }:
            monkeypatch.setenv(key, value)

    response = client.post(
        "/api/v1/knowledge/chunks",
        json={
            "chunks": [
                {
                    "chunk_id": "malicious-1",
                    "document_id": "malicious",
                    "title": "외부 입력",
                    "content": "공개 데모 데이터베이스에 저장되면 안 되는 내용입니다.",
                    "chunk_index": 0,
                }
            ]
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "demo_write_disabled"
