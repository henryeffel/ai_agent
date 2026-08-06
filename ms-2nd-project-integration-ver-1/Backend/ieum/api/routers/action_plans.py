from typing import Annotated

from fastapi import APIRouter, Depends

from ieum.providers.llm.nvidia import LLMProviderError
from ieum.repositories.action_plan import (
    ActionPlanNotFoundError,
    DuplicateActionIdError,
    InvalidStateTransitionError,
)
from ieum.schemas.action_plan import (
    ActionPlanCreate,
    ActionPlanDecision,
    ActionPlanResponse,
    GroundedActionPlanCreate,
)
from ieum.services.action_workflow import (
    ActorPermissionError,
    InsufficientEvidenceError,
    get_action_workflow_service,
)
from ieum.security.dependencies import get_actor_context
from ieum.security.identity import ActorContext
from ieum.api.errors import ApiException, ERROR_RESPONSES
from ieum.config import get_settings
from ieum.demo.scope import scope_demo_meeting_id


router = APIRouter(prefix="/api/v1/action-plans", tags=["action-plans"])


@router.post("", response_model=ActionPlanResponse, status_code=201)
def create_action_plan(request: ActionPlanCreate):
    if get_settings().app_mode == "demo":
        request = request.model_copy(
            update={"meeting_id": scope_demo_meeting_id(request.meeting_id)}
        )
    try:
        return get_action_workflow_service().create_plan(request)
    except DuplicateActionIdError as exc:
        raise ApiException(409, "duplicate_action", str(exc)) from exc


@router.post(
    "/grounded",
    response_model=ActionPlanResponse,
    status_code=201,
    operation_id="createGroundedActionPlan",
    summary="Create an evidence-grounded action plan",
    description="Analyze the transcript, retrieve organization knowledge, and create a pending plan. No tool is executed by this operation.",
    responses=ERROR_RESPONSES,
)
def create_grounded_action_plan(request: GroundedActionPlanCreate):
    if get_settings().app_mode == "demo":
        request = request.model_copy(
            update={"meeting_id": scope_demo_meeting_id(request.meeting_id)}
        )
    try:
        return get_action_workflow_service().create_grounded_plan(request)
    except InsufficientEvidenceError as exc:
        raise ApiException(422, "insufficient_evidence", str(exc)) from exc
    except LLMProviderError as exc:
        raise ApiException(
            502, "llm_invalid_response", str(exc), retryable=True
        ) from exc
    except DuplicateActionIdError as exc:
        raise ApiException(409, "duplicate_action", str(exc)) from exc


@router.get(
    "/{plan_id}",
    response_model=ActionPlanResponse,
    operation_id="getActionPlan",
    summary="Get action plan status and tool results",
    description="Return approval state, evidence identifiers, and per-tool execution results.",
    responses=ERROR_RESPONSES,
)
def get_action_plan(plan_id: str):
    try:
        return get_action_workflow_service().get_plan(plan_id)
    except ActionPlanNotFoundError as exc:
        raise ApiException(404, "plan_not_found", str(exc)) from exc


@router.post(
    "/{plan_id}/approve",
    response_model=ActionPlanResponse,
    operation_id="approveActionPlan",
    summary="Approve an action plan without executing it",
    description="Apply the human approval gate. The caller must have the approver role. Execution remains a separate explicit operation.",
    responses=ERROR_RESPONSES,
)
def approve_action_plan(
    plan_id: str,
    request: ActionPlanDecision,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
):
    try:
        return get_action_workflow_service().approve_plan(plan_id, actor)
    except ActionPlanNotFoundError as exc:
        raise ApiException(404, "plan_not_found", str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise ApiException(409, "invalid_state_transition", str(exc)) from exc
    except ActorPermissionError as exc:
        raise ApiException(403, "authorization_error", str(exc)) from exc


@router.post("/{plan_id}/reject", response_model=ActionPlanResponse)
def reject_action_plan(
    plan_id: str,
    request: ActionPlanDecision,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
):
    try:
        return get_action_workflow_service().reject_plan(plan_id, actor)
    except ActionPlanNotFoundError as exc:
        raise ApiException(404, "plan_not_found", str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise ApiException(409, "invalid_state_transition", str(exc)) from exc
    except ActorPermissionError as exc:
        raise ApiException(403, "authorization_error", str(exc)) from exc


@router.post(
    "/{plan_id}/execute",
    response_model=ActionPlanResponse,
    operation_id="executeApprovedActionPlan",
    summary="Execute tools for an approved action plan",
    description="Execute Calendar, To-do, or Email actions only after approval. Repeated or concurrent execution is rejected.",
    responses=ERROR_RESPONSES,
)
def execute_action_plan(
    plan_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
):
    try:
        return get_action_workflow_service().execute_plan(plan_id, actor)
    except ActionPlanNotFoundError as exc:
        raise ApiException(404, "plan_not_found", str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise ApiException(409, "invalid_state_transition", str(exc)) from exc
    except ActorPermissionError as exc:
        raise ApiException(403, "authorization_error", str(exc)) from exc
