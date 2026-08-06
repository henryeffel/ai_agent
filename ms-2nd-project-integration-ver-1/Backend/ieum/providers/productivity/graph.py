import os
import time
from datetime import timezone
from urllib.parse import quote

import httpx

from ieum.providers.productivity.base import (
    ProductivityConfigurationError,
    ProductivityProvider,
    ProductivityProviderError,
    ProductivityRateLimitedError,
    ProductivityTimeoutError,
    ProductivityUnauthorizedError,
)
from ieum.providers.productivity.graph_auth import GraphTokenProvider
from ieum.schemas.productivity import (
    CalendarPayload,
    EmailPayload,
    TodoPayload,
    ToolExecutionResult,
    ToolType,
)


class MicrosoftGraphProductivityProvider(ProductivityProvider):
    def __init__(
        self,
        token_provider: GraphTokenProvider,
        client: httpx.Client | None = None,
        *,
        auth_mode: str | None = None,
    ):
        self.token_provider = token_provider
        self.client = client or httpx.Client(
            timeout=float(os.getenv("PRODUCTIVITY_TIMEOUT_SECONDS", "10"))
        )
        self.auth_mode = (auth_mode or os.getenv("GRAPH_AUTH_MODE", "delegated")).lower()
        if self.auth_mode not in {"delegated", "application"}:
            raise ProductivityConfigurationError(
                "GRAPH_AUTH_MODE는 delegated 또는 application이어야 합니다."
            )

    @property
    def provider_name(self) -> str:
        return "microsoft_graph"

    def create_calendar_event(self, action_id, payload: CalendarPayload):
        body = {
            "subject": payload.title,
            "body": {
                "contentType": "text",
                "content": payload.description or "",
            },
            "start": _date_time(payload.start_at),
            "end": _date_time(payload.end_at),
            "attendees": [
                {
                    "emailAddress": {"address": str(address)},
                    "type": "required",
                }
                for address in payload.attendees
            ],
            "transactionId": action_id,
        }
        return self._post(action_id, ToolType.CALENDAR, self._user_path("events"), body)

    def create_todo(self, action_id, payload: TodoPayload):
        if self.auth_mode == "application":
            raise ProductivityConfigurationError(
                "Microsoft Graph To Do task 생성은 delegated Tasks.ReadWrite가 필요합니다."
            )
        list_id = os.getenv("GRAPH_TODO_LIST_ID", "").strip()
        if not list_id:
            raise ProductivityConfigurationError(
                "GRAPH_TODO_LIST_ID가 설정되지 않았습니다."
            )
        body = {
            "title": payload.title,
            "body": {
                "content": payload.description or "",
                "contentType": "text",
            },
        }
        if payload.due_at:
            body["dueDateTime"] = _date_time(payload.due_at)
        path = f"/me/todo/lists/{quote(list_id, safe='')}/tasks"
        return self._post(action_id, ToolType.TODO, path, body)

    def send_email(self, action_id, payload: EmailPayload):
        body = {
            "message": {
                "subject": payload.subject,
                "body": {"contentType": "text", "content": payload.body},
                "toRecipients": [
                    {"emailAddress": {"address": str(address)}}
                    for address in payload.recipients
                ],
            },
            "saveToSentItems": True,
        }
        return self._post(action_id, ToolType.EMAIL, self._user_path("sendMail"), body)

    def _user_path(self, suffix: str) -> str:
        if self.auth_mode == "delegated":
            return f"/me/{suffix}"
        user_id = os.getenv("GRAPH_USER_ID", "").strip()
        if not user_id:
            raise ProductivityConfigurationError(
                "application 모드에는 GRAPH_USER_ID가 필요합니다."
            )
        return f"/users/{quote(user_id, safe='')}/{suffix}"

    def _post(self, action_id, tool, path, body):
        started_at = time.perf_counter()
        token = self.token_provider.get_access_token()
        try:
            response = self.client.post(
                f"https://graph.microsoft.com/v1.0{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        except httpx.TimeoutException as exc:
            raise ProductivityTimeoutError() from exc
        except httpx.RequestError as exc:
            raise ProductivityProviderError(
                "network_error", "Microsoft Graph 네트워크 요청에 실패했습니다."
            ) from exc
        if response.status_code == 401:
            raise ProductivityUnauthorizedError()
        if response.status_code == 403:
            raise ProductivityProviderError(
                "authorization_error", "Microsoft Graph 호출 권한이 없습니다."
            )
        if response.status_code == 429:
            raise ProductivityRateLimitedError(
                _retry_after_seconds(response.headers.get("Retry-After"))
            )
        if 400 <= response.status_code < 500:
            raise ProductivityProviderError(
                "upstream_4xx", "Microsoft Graph가 요청을 거부했습니다."
            )
        if response.status_code >= 500:
            raise ProductivityProviderError(
                "upstream_5xx", "Microsoft Graph에서 오류가 발생했습니다."
            )
        data = {}
        if response.content:
            try:
                data = response.json()
            except ValueError as exc:
                raise ProductivityProviderError(
                    "invalid_response", "Microsoft Graph 응답 형식이 올바르지 않습니다."
                ) from exc
        resource_id = data.get("id") or response.headers.get("request-id")
        return ToolExecutionResult(
            success=True,
            provider=self.provider_name,
            tool=tool,
            external_resource_id=resource_id,
            latency_ms=max(1, int((time.perf_counter() - started_at) * 1000)),
        )


def _date_time(value):
    utc_value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return {"dateTime": utc_value.isoformat(), "timeZone": "UTC"}


def _retry_after_seconds(value):
    try:
        return max(0, int(value)) if value is not None else None
    except ValueError:
        return None
