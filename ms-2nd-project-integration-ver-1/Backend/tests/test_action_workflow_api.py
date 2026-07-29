import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["APP_MODE"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["PRODUCTIVITY_PROVIDER"] = "mock"

from ieum.database import get_engine, get_session_factory
from ieum.providers.productivity.factory import get_productivity_provider
from ieum.services.action_workflow import get_action_workflow_service
from main import app


client = TestClient(app)
actor = "alfzm102435@gmail.com"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    database_path = tmp_path / "workflow.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "success")

    get_action_workflow_service.cache_clear()
    get_productivity_provider.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()

    yield

    get_action_workflow_service.cache_clear()
    get_productivity_provider.cache_clear()
    engine = get_engine()
    engine.dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()


def _calendar_action(action_id=None):
    return {
        "action_id": action_id or f"calendar-{uuid4()}",
        "payload": {
            "tool": "calendar",
            "title": "후속 검토 회의",
            "start_at": "2026-08-05T14:00:00+09:00",
            "end_at": "2026-08-05T15:00:00+09:00",
            "attendees": [],
        },
    }


def _email_action(action_id=None):
    return {
        "action_id": action_id or f"email-{uuid4()}",
        "payload": {
            "tool": "email",
            "recipients": [actor],
            "subject": "IEUM 테스트",
            "body": "Mock Provider Workflow 테스트입니다.",
        },
    }


def _create_plan(actions=None):
    response = client.post(
        "/api/v1/action-plans",
        json={
            "meeting_id": f"meeting-{uuid4()}",
            "actions": actions or [_calendar_action()],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_unapproved_plan_cannot_execute():
    plan = _create_plan()

    response = client.post(f"/api/v1/action-plans/{plan['id']}/execute")

    assert response.status_code == 409
    stored = client.get(f"/api/v1/action-plans/{plan['id']}").json()
    assert stored["status"] == "PENDING_APPROVAL"
    assert stored["actions"][0]["attempts"] == 0


def test_approved_plan_executes_once_and_stores_resource_id():
    plan = _create_plan()

    approved = client.post(
        f"/api/v1/action-plans/{plan['id']}/approve",
        json={"actor": actor},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    executed = client.post(f"/api/v1/action-plans/{plan['id']}/execute")
    assert executed.status_code == 200
    body = executed.json()
    assert body["status"] == "SUCCEEDED"
    assert body["actions"][0]["status"] == "SUCCEEDED"
    assert body["actions"][0]["attempts"] == 1
    assert body["actions"][0]["external_resource_id"]

    duplicate = client.post(f"/api/v1/action-plans/{plan['id']}/execute")
    assert duplicate.status_code == 409

    stored = client.get(f"/api/v1/action-plans/{plan['id']}").json()
    assert stored["actions"][0]["attempts"] == 1


def test_partial_failure_is_recorded(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "partial_failure")
    plan = _create_plan([_calendar_action(), _email_action()])
    client.post(
        f"/api/v1/action-plans/{plan['id']}/approve",
        json={"actor": actor},
    )

    response = client.post(f"/api/v1/action-plans/{plan['id']}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PARTIALLY_SUCCEEDED"
    assert [action["status"] for action in body["actions"]] == [
        "SUCCEEDED",
        "FAILED",
    ]
    assert body["actions"][1]["error_code"] == "mock_email_failure"


def test_timeout_marks_plan_and_action_failed(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "timeout")
    plan = _create_plan()
    client.post(
        f"/api/v1/action-plans/{plan['id']}/approve",
        json={"actor": actor},
    )

    response = client.post(f"/api/v1/action-plans/{plan['id']}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["actions"][0]["status"] == "FAILED"
    assert body["actions"][0]["error_code"] == "timeout"


def test_rejected_plan_cannot_be_approved_or_executed():
    plan = _create_plan()

    rejected = client.post(
        f"/api/v1/action-plans/{plan['id']}/reject",
        json={"actor": actor},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"

    approve = client.post(
        f"/api/v1/action-plans/{plan['id']}/approve",
        json={"actor": actor},
    )
    execute = client.post(f"/api/v1/action-plans/{plan['id']}/execute")

    assert approve.status_code == 409
    assert execute.status_code == 409


def test_duplicate_action_id_is_rejected():
    action_id = f"duplicate-{uuid4()}"
    _create_plan([_calendar_action(action_id)])

    response = client.post(
        "/api/v1/action-plans",
        json={
            "meeting_id": f"meeting-{uuid4()}",
            "actions": [_calendar_action(action_id)],
        },
    )

    assert response.status_code == 409


def test_concurrent_execute_requests_only_claim_plan_once():
    plan = _create_plan()
    client.post(
        f"/api/v1/action-plans/{plan['id']}/approve",
        json={"actor": actor},
    )

    def execute():
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                f"/api/v1/action-plans/{plan['id']}/execute"
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: execute(), range(2)))

    assert sorted(statuses) == [200, 409]
    stored = client.get(f"/api/v1/action-plans/{plan['id']}").json()
    assert stored["status"] == "SUCCEEDED"
    assert stored["actions"][0]["attempts"] == 1
