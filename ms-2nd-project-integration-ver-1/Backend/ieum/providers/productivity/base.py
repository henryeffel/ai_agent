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


class ProductivityConfigurationError(ProductivityProviderError):
    def __init__(self, message: str):
        super().__init__(code="configuration_error", message=message)


class ProductivityRateLimitedError(ProductivityProviderError):
    def __init__(self, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        suffix = (
            f" {retry_after_seconds}초 후 다시 시도할 수 있습니다."
            if retry_after_seconds is not None
            else ""
        )
        super().__init__(
            code="rate_limited",
            message=f"Microsoft Graph 요청 한도를 초과했습니다.{suffix}",
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
