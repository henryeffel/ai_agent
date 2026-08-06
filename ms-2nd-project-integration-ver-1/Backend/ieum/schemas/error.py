from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ApiError
