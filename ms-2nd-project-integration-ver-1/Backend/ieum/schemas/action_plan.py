from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ieum.schemas.productivity import ProductivityPayload, ToolType


class EvidenceDetail(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    category: str
    source: str | None
    excerpt: str
    similarity_score: float


class ActionPlanStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    PARTIALLY_SUCCEEDED = "PARTIALLY_SUCCEEDED"
    FAILED = "FAILED"


class ActionExecutionStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=100)
    payload: ProductivityPayload


class ActionPlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: str = Field(min_length=1, max_length=100)
    evidence_chunk_ids: list[str] = Field(
        default_factory=list,
        max_length=20,
    )
    evidence: list[EvidenceDetail] = Field(default_factory=list, max_length=20)
    actions: list[ActionCreate] = Field(min_length=1, max_length=50)


class GroundedActionPlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: str = Field(min_length=1, max_length=100)
    transcript: str = Field(min_length=10, max_length=100_000)
    category: str | None = Field(default=None, max_length=50)
    top_k: int = Field(default=3, ge=1, le=20)
    min_score: float = Field(default=0.2, ge=-1.0, le=1.0)


class ActionPlanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Kept temporarily for React client compatibility. Authorization and audit
    # identity come from ActorContext, never from this user-controlled value.
    actor: EmailStr | None = None


class ActionExecutionResponse(BaseModel):
    id: str
    action_id: str
    tool: ToolType
    payload: dict
    status: ActionExecutionStatus
    attempts: int
    provider: str | None
    external_resource_id: str | None
    latency_ms: int | None
    error_code: str | None
    error_message: str | None


class ActionPlanResponse(BaseModel):
    id: str
    meeting_id: str
    evidence_chunk_ids: list[str]
    evidence: list[EvidenceDetail]
    status: ActionPlanStatus
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    actions: list[ActionExecutionResponse]
