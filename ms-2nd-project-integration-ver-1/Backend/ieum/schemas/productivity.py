from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ToolType(str, Enum):
    CALENDAR = "calendar"
    TODO = "todo"
    EMAIL = "email"


class CalendarPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal[ToolType.CALENDAR] = ToolType.CALENDAR
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    attendees: list[EmailStr] = Field(default_factory=list, max_length=50)
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at은 start_at보다 이후여야 합니다.")
        return self


class TodoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal[ToolType.TODO] = ToolType.TODO
    title: str = Field(min_length=1, max_length=300)
    due_at: datetime | None = None
    description: str | None = Field(default=None, max_length=5000)


class EmailPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal[ToolType.EMAIL] = ToolType.EMAIL
    recipients: list[EmailStr] = Field(min_length=1, max_length=20)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20_000)


ProductivityPayload = Annotated[
    Union[CalendarPayload, TodoPayload, EmailPayload],
    Field(discriminator="tool"),
]


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    provider: str
    tool: ToolType
    external_resource_id: str | None = None
    latency_ms: int = Field(ge=0)
    error_code: str | None = None
    error_message: str | None = None
