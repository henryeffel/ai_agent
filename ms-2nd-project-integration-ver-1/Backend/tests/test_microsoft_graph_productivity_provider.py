import json

import httpx
import pytest

from ieum.providers.productivity.base import (
    ProductivityConfigurationError,
    ProductivityProviderError,
    ProductivityRateLimitedError,
)
from ieum.providers.productivity.graph import MicrosoftGraphProductivityProvider
from ieum.providers.productivity.graph_auth import (
    ClientCredentialsGraphTokenProvider,
    GraphTokenProvider,
)
from ieum.schemas.productivity import CalendarPayload, EmailPayload, TodoPayload


class StaticTokenProvider(GraphTokenProvider):
    def get_access_token(self):
        return "test-access-token"


def _provider(handler, auth_mode="delegated"):
    return MicrosoftGraphProductivityProvider(
        StaticTokenProvider(),
        httpx.Client(transport=httpx.MockTransport(handler)),
        auth_mode=auth_mode,
    )


def test_delegated_provider_maps_calendar_todo_and_email(monkeypatch):
    monkeypatch.setenv("GRAPH_TODO_LIST_ID", "tasks/list")
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("sendMail"):
            return httpx.Response(202, headers={"request-id": "mail-request-1"})
        return httpx.Response(201, json={"id": f"resource-{len(requests)}"})

    provider = _provider(handler)
    calendar = provider.create_calendar_event(
        "calendar-action",
        CalendarPayload(
            title="검토 회의",
            start_at="2026-08-07T10:00:00+09:00",
            end_at="2026-08-07T11:00:00+09:00",
            attendees=["member@example.com"],
        ),
    )
    todo = provider.create_todo(
        "todo-action",
        TodoPayload(title="자료 작성", due_at="2026-08-08T18:00:00+09:00"),
    )
    email = provider.send_email(
        "email-action",
        EmailPayload(
            recipients=["member@example.com"], subject="회의 결과", body="본문"
        ),
    )

    assert [request.url.raw_path for request in requests] == [
        b"/v1.0/me/events",
        b"/v1.0/me/todo/lists/tasks%2Flist/tasks",
        b"/v1.0/me/sendMail",
    ]
    assert all(
        request.headers["authorization"] == "Bearer test-access-token"
        for request in requests
    )
    calendar_body = json.loads(requests[0].content)
    assert calendar_body["transactionId"] == "calendar-action"
    assert calendar_body["start"]["timeZone"] == "UTC"
    assert calendar.external_resource_id == "resource-1"
    assert todo.external_resource_id == "resource-2"
    assert email.external_resource_id == "mail-request-1"


def test_application_mode_uses_target_user_for_calendar_and_mail(monkeypatch):
    monkeypatch.setenv("GRAPH_USER_ID", "user@example.com")
    paths = []

    def handler(request):
        paths.append(request.url.raw_path)
        return httpx.Response(202, headers={"request-id": "request-1"})

    provider = _provider(handler, auth_mode="application")
    provider.send_email(
        "email-app",
        EmailPayload(
            recipients=["member@example.com"], subject="회의 결과", body="본문"
        ),
    )

    assert paths == [b"/v1.0/users/user%40example.com/sendMail"]


def test_application_mode_rejects_todo_even_with_list_id(monkeypatch):
    monkeypatch.setenv("GRAPH_TODO_LIST_ID", "list-1")
    provider = _provider(lambda request: httpx.Response(201, json={"id": "x"}), "application")

    with pytest.raises(ProductivityConfigurationError, match="delegated"):
        provider.create_todo("todo-app", TodoPayload(title="자료 작성"))


def test_rate_limit_preserves_retry_after_without_automatic_write_retry():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "17"}, json={"error": {"message": "sensitive"}})

    provider = _provider(handler)
    with pytest.raises(ProductivityRateLimitedError) as caught:
        provider.send_email(
            "email-rate",
            EmailPayload(
                recipients=["member@example.com"], subject="회의 결과", body="본문"
            ),
        )

    assert calls == 1
    assert caught.value.retry_after_seconds == 17
    assert "sensitive" not in caught.value.message


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "unauthorized"), (403, "authorization_error"), (400, "upstream_4xx"), (500, "upstream_5xx")],
)
def test_maps_graph_errors_without_response_body(status, code):
    provider = _provider(
        lambda request: httpx.Response(status, text="sensitive graph response")
    )
    with pytest.raises(ProductivityProviderError) as caught:
        provider.send_email(
            "email-error",
            EmailPayload(
                recipients=["member@example.com"], subject="회의 결과", body="본문"
            ),
        )
    assert caught.value.code == code
    assert "sensitive" not in caught.value.message


def test_client_credentials_token_is_cached(monkeypatch):
    monkeypatch.setenv("GRAPH_TENANT_ID", "tenant-1")
    monkeypatch.setenv("GRAPH_CLIENT_ID", "client-1")
    monkeypatch.setenv("GRAPH_CLIENT_SECRET", "not-a-real-secret")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={"access_token": "cached-token", "expires_in": 3600},
        )

    provider = ClientCredentialsGraphTokenProvider(
        httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert provider.get_access_token() == "cached-token"
    assert provider.get_access_token() == "cached-token"
    assert len(calls) == 1
    assert calls[0].url.path == "/tenant-1/oauth2/v2.0/token"
