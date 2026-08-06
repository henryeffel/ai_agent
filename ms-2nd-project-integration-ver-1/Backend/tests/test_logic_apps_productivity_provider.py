import httpx
import pytest

from ieum.providers.productivity.base import (
    ProductivityConfigurationError,
    ProductivityProviderError,
    ProductivityTimeoutError,
)
from ieum.providers.productivity.logic_apps import LogicAppsMicrosoft365Provider
from ieum.schemas.productivity import CalendarPayload, EmailPayload, TodoPayload


def _provider(handler):
    return LogicAppsMicrosoft365Provider(
        httpx.Client(transport=httpx.MockTransport(handler))
    )


def _set_urls(monkeypatch):
    monkeypatch.setenv("LOGIC_APP_CALENDAR_URL", "https://logic.test/calendar")
    monkeypatch.setenv("LOGIC_APP_TODO_URL", "https://logic.test/todo")
    monkeypatch.setenv("LOGIC_APP_EMAIL_URL", "https://logic.test/email")


def test_executes_each_tool_and_returns_resource_id(monkeypatch):
    _set_urls(monkeypatch)
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"resource_id": "external-123"})

    provider = _provider(handler)
    calendar = provider.create_calendar_event(
        "calendar-1",
        CalendarPayload(
            title="검토 회의",
            start_at="2026-08-07T10:00:00+09:00",
            end_at="2026-08-07T11:00:00+09:00",
        ),
    )
    todo = provider.create_todo("todo-1", TodoPayload(title="자료 작성"))
    email = provider.send_email(
        "email-1",
        EmailPayload(
            recipients=["tester@example.com"], subject="결과", body="본문"
        ),
    )

    assert len(requests) == 3
    assert {calendar.external_resource_id, todo.external_resource_id, email.external_resource_id} == {"external-123"}
    assert all(result.provider == "logic_apps_microsoft_365" for result in (calendar, todo, email))


def test_missing_url_is_not_treated_as_success(monkeypatch):
    monkeypatch.delenv("LOGIC_APP_EMAIL_URL", raising=False)
    provider = _provider(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ProductivityConfigurationError):
        provider.send_email(
            "email-2",
            EmailPayload(recipients=["tester@example.com"], subject="결과", body="본문"),
        )


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "unauthorized"), (403, "authorization_error"), (429, "rate_limited"), (400, "upstream_4xx"), (500, "upstream_5xx")],
)
def test_maps_http_errors_without_exposing_response_body(monkeypatch, status, code):
    _set_urls(monkeypatch)
    provider = _provider(
        lambda request: httpx.Response(status, text="sensitive upstream body")
    )
    with pytest.raises(ProductivityProviderError) as caught:
        provider.create_todo("todo-error", TodoPayload(title="자료 작성"))
    assert caught.value.code == code
    assert "sensitive" not in caught.value.message


def test_rejects_invalid_json(monkeypatch):
    _set_urls(monkeypatch)
    provider = _provider(
        lambda request: httpx.Response(200, text="not-json")
    )
    with pytest.raises(ProductivityProviderError) as caught:
        provider.create_todo("todo-json", TodoPayload(title="자료 작성"))
    assert caught.value.code == "invalid_response"


def test_maps_timeout(monkeypatch):
    _set_urls(monkeypatch)

    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(ProductivityTimeoutError):
        _provider(handler).create_todo("todo-timeout", TodoPayload(title="자료 작성"))
