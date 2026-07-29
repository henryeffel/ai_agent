from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1, max_length=500)
    assignee: str | None = Field(default=None, max_length=100)
    due_date: date | None = None


class MeetingAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=3000)
    decisions: list[str] = Field(default_factory=list, max_length=50)
    action_items: list[ActionItem] = Field(default_factory=list, max_length=100)
    open_issues: list[str] = Field(default_factory=list, max_length=50)


class MeetingAnalysisRequest(BaseModel):
    transcript: str = Field(min_length=10, max_length=100_000)


class MeetingAnalysisResponse(BaseModel):
    status: str = "success"
    provider: str
    model: str
    data: MeetingAnalysis
