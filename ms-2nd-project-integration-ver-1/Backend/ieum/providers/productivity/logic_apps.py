import os
import time

import httpx

from ieum.providers.productivity.base import (
    ProductivityConfigurationError,
    ProductivityProvider,
    ProductivityProviderError,
    ProductivityTimeoutError,
    ProductivityUnauthorizedError,
)
from ieum.schemas.productivity import (
    CalendarPayload,
    EmailPayload,
    TodoPayload,
    ToolExecutionResult,
    ToolType,
)


class LogicAppsMicrosoft365Provider(ProductivityProvider):
    def __init__(self, client: httpx.Client | None = None):
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=float(os.getenv("PRODUCTIVITY_TIMEOUT_SECONDS", "10"))
        )

    @property
    def provider_name(self) -> str:
        return "logic_apps_microsoft_365"

    def create_calendar_event(self, action_id, payload: CalendarPayload):
        return self._execute(
            action_id,
            ToolType.CALENDAR,
            "LOGIC_APP_CALENDAR_URL",
            payload.model_dump(mode="json", exclude={"tool"}),
        )

    def create_todo(self, action_id, payload: TodoPayload):
        return self._execute(
            action_id,
            ToolType.TODO,
            "LOGIC_APP_TODO_URL",
            payload.model_dump(mode="json", exclude={"tool"}),
        )

    def send_email(self, action_id, payload: EmailPayload):
        return self._execute(
            action_id,
            ToolType.EMAIL,
            "LOGIC_APP_EMAIL_URL",
            payload.model_dump(mode="json", exclude={"tool"}),
        )

    def _execute(self, action_id, tool, environment_key, payload):
        url = os.getenv(environment_key)
        if not url:
            raise ProductivityConfigurationError(
                f"{environment_key}가 설정되지 않았습니다."
            )
        started_at = time.perf_counter()
        try:
            response = self._client.post(
                url,
                json={"action_id": action_id, **payload},
            )
        except httpx.TimeoutException as exc:
            raise ProductivityTimeoutError() from exc
        except httpx.RequestError as exc:
            raise ProductivityProviderError(
                "network_error", "Logic Apps 네트워크 요청에 실패했습니다."
            ) from exc

        if response.status_code == 401:
            raise ProductivityUnauthorizedError()
        if response.status_code == 403:
            raise ProductivityProviderError(
                "authorization_error", "Logic Apps 호출 권한이 없습니다."
            )
        if response.status_code == 429:
            raise ProductivityProviderError(
                "rate_limited", "Logic Apps 요청 한도를 초과했습니다."
            )
        if 400 <= response.status_code < 500:
            raise ProductivityProviderError(
                "upstream_4xx", "Logic Apps가 요청을 거부했습니다."
            )
        if response.status_code >= 500:
            raise ProductivityProviderError(
                "upstream_5xx", "Logic Apps에서 오류가 발생했습니다."
            )

        try:
            data = response.json() if response.content else {}
        except ValueError as exc:
            raise ProductivityProviderError(
                "invalid_response", "Logic Apps 응답 형식이 올바르지 않습니다."
            ) from exc
        resource_id = data.get("resource_id") or data.get("id")
        return ToolExecutionResult(
            success=True,
            provider=self.provider_name,
            tool=tool,
            external_resource_id=str(resource_id) if resource_id else None,
            latency_ms=max(1, int((time.perf_counter() - started_at) * 1000)),
        )
