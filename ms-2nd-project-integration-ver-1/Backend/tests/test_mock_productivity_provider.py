import os

import pytest
from pydantic import ValidationError

from ieum.providers.productivity.base import (
    DuplicateActionError,
    ProductivityTimeoutError,
    ProductivityUnauthorizedError,
)
from ieum.providers.productivity.mock import MockMicrosoft365Provider
from ieum.schemas.productivity import (
    CalendarPayload,
    EmailPayload,
    TodoPayload,
)


provider = MockMicrosoft365Provider()


def _calendar_payload():
    return CalendarPayload(
        title="후속 검토 회의",
        start_at="2026-08-05T14:00:00+09:00",
        end_at="2026-08-05T15:00:00+09:00",
    )


def _todo_payload():
    return TodoPayload(
        title="제품 소개서 작성",
        due_at="2026-08-03T18:00:00+09:00",
    )


def _email_payload():
    return EmailPayload(
        recipients=["alfzm102435@gmail.com"],
        subject="IEUM 테스트",
        body="Mock Provider 테스트입니다.",
    )


def test_success_scenario_returns_external_resource_ids(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "success")

    calendar = provider.create_calendar_event("calendar-1", _calendar_payload())
    todo = provider.create_todo("todo-1", _todo_payload())
    email = provider.send_email("email-1", _email_payload())

    assert calendar.success is True
    assert calendar.external_resource_id == "mock-calendar-calendar-1"
    assert todo.external_resource_id == "mock-todo-todo-1"
    assert email.external_resource_id == "mock-email-email-1"


def test_unauthorized_scenario(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "unauthorized")

    with pytest.raises(ProductivityUnauthorizedError):
        provider.create_todo("todo-2", _todo_payload())


def test_timeout_scenario(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "timeout")

    with pytest.raises(ProductivityTimeoutError):
        provider.create_calendar_event("calendar-2", _calendar_payload())


def test_duplicate_action_scenario(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "duplicate_action")

    with pytest.raises(DuplicateActionError):
        provider.send_email("email-2", _email_payload())


def test_partial_failure_only_fails_email(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "partial_failure")

    calendar = provider.create_calendar_event("calendar-3", _calendar_payload())
    todo = provider.create_todo("todo-3", _todo_payload())
    email = provider.send_email("email-3", _email_payload())

    assert calendar.success is True
    assert todo.success is True
    assert email.success is False
    assert email.error_code == "mock_email_failure"


def test_unknown_scenario_is_rejected(monkeypatch):
    monkeypatch.setenv("MOCK_PRODUCTIVITY_SCENARIO", "not-supported")

    with pytest.raises(RuntimeError, match="지원하지 않는 Mock 시나리오"):
        provider.create_todo("todo-4", _todo_payload())


def test_calendar_rejects_invalid_time_range():
    with pytest.raises(ValidationError, match="end_at"):
        CalendarPayload(
            title="잘못된 일정",
            start_at="2026-08-05T15:00:00+09:00",
            end_at="2026-08-05T14:00:00+09:00",
        )
