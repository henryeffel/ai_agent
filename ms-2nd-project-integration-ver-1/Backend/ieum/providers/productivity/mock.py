import os
import time
from enum import Enum

from ieum.providers.productivity.base import (
    DuplicateActionError,
    ProductivityProvider,
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


class MockProductivityScenario(str, Enum):
    SUCCESS = "success"
    UNAUTHORIZED = "unauthorized"
    TIMEOUT = "timeout"
    PARTIAL_FAILURE = "partial_failure"
    DUPLICATE_ACTION = "duplicate_action"


class MockMicrosoft365Provider(ProductivityProvider):
    @property
    def provider_name(self) -> str:
        return "mock_microsoft_365"

    def create_calendar_event(
        self,
        action_id: str,
        payload: CalendarPayload,
    ) -> ToolExecutionResult:
        return self._execute(action_id, ToolType.CALENDAR)

    def create_todo(
        self,
        action_id: str,
        payload: TodoPayload,
    ) -> ToolExecutionResult:
        return self._execute(action_id, ToolType.TODO)

    def send_email(
        self,
        action_id: str,
        payload: EmailPayload,
    ) -> ToolExecutionResult:
        return self._execute(action_id, ToolType.EMAIL)

    def _execute(
        self,
        action_id: str,
        tool: ToolType,
    ) -> ToolExecutionResult:
        scenario = self._scenario()
        started_at = time.perf_counter()

        if scenario == MockProductivityScenario.UNAUTHORIZED:
            raise ProductivityUnauthorizedError()
        if scenario == MockProductivityScenario.TIMEOUT:
            raise ProductivityTimeoutError()
        if scenario == MockProductivityScenario.DUPLICATE_ACTION:
            raise DuplicateActionError()
        if (
            scenario == MockProductivityScenario.PARTIAL_FAILURE
            and tool == ToolType.EMAIL
        ):
            return ToolExecutionResult(
                success=False,
                provider=self.provider_name,
                tool=tool,
                latency_ms=self._latency_ms(started_at),
                error_code="mock_email_failure",
                error_message="부분 실패 검증을 위한 Mock 이메일 오류입니다.",
            )

        return ToolExecutionResult(
            success=True,
            provider=self.provider_name,
            tool=tool,
            external_resource_id=f"mock-{tool.value}-{action_id}",
            latency_ms=self._latency_ms(started_at),
        )

    @staticmethod
    def _latency_ms(started_at: float) -> int:
        return max(1, int((time.perf_counter() - started_at) * 1000))

    @staticmethod
    def _scenario() -> MockProductivityScenario:
        value = os.getenv(
            "MOCK_PRODUCTIVITY_SCENARIO",
            MockProductivityScenario.SUCCESS.value,
        ).lower()
        try:
            return MockProductivityScenario(value)
        except ValueError as exc:
            supported = ", ".join(item.value for item in MockProductivityScenario)
            raise RuntimeError(
                f"지원하지 않는 Mock 시나리오입니다: {value}. 지원: {supported}"
            ) from exc
