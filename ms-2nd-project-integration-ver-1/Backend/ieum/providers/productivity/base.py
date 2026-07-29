from abc import ABC, abstractmethod

from ieum.schemas.productivity import (
    CalendarPayload,
    EmailPayload,
    TodoPayload,
    ToolExecutionResult,
)


class ProductivityProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ProductivityUnauthorizedError(ProductivityProviderError):
    def __init__(self):
        super().__init__(
            code="unauthorized",
            message="Microsoft 365 인증에 실패했습니다.",
        )


class ProductivityTimeoutError(ProductivityProviderError):
    def __init__(self):
        super().__init__(
            code="timeout",
            message="Microsoft 365 요청 시간이 초과되었습니다.",
        )


class DuplicateActionError(ProductivityProviderError):
    def __init__(self):
        super().__init__(
            code="duplicate_action",
            message="이미 실행된 Action입니다.",
        )


class ProductivityProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a stable provider identifier."""

    @abstractmethod
    def create_calendar_event(
        self,
        action_id: str,
        payload: CalendarPayload,
    ) -> ToolExecutionResult:
        """Create an Outlook calendar event."""

    @abstractmethod
    def create_todo(
        self,
        action_id: str,
        payload: TodoPayload,
    ) -> ToolExecutionResult:
        """Create a Microsoft To Do task."""

    @abstractmethod
    def send_email(
        self,
        action_id: str,
        payload: EmailPayload,
    ) -> ToolExecutionResult:
        """Send an email."""
