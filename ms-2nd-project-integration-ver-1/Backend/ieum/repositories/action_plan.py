from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ieum.models.action_plan import ActionExecutionModel, ActionPlanModel
from ieum.schemas.action_plan import (
    ActionExecutionStatus,
    ActionPlanCreate,
    ActionPlanStatus,
)


class ActionPlanNotFoundError(RuntimeError):
    pass


class InvalidStateTransitionError(RuntimeError):
    pass


class DuplicateActionIdError(RuntimeError):
    pass


class ActionPlanRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, request: ActionPlanCreate) -> ActionPlanModel:
        plan = ActionPlanModel(
            id=str(uuid4()),
            meeting_id=request.meeting_id,
            evidence_chunk_ids=request.evidence_chunk_ids,
            status=ActionPlanStatus.PENDING_APPROVAL.value,
        )
        for item in request.actions:
            payload = item.payload.model_dump(mode="json")
            plan.actions.append(
                ActionExecutionModel(
                    id=str(uuid4()),
                    action_id=item.action_id,
                    tool=item.payload.tool.value,
                    payload=payload,
                    status=ActionExecutionStatus.PENDING.value,
                )
            )
        self.session.add(plan)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateActionIdError(
                "이미 존재하는 action_id가 포함되어 있습니다."
            ) from exc
        return self.get(plan.id)

    def get(self, plan_id: str) -> ActionPlanModel:
        plan = self.session.get(ActionPlanModel, plan_id)
        if not plan:
            raise ActionPlanNotFoundError("Action Plan을 찾을 수 없습니다.")
        return plan

    def approve(self, plan_id: str, actor: str) -> ActionPlanModel:
        now = datetime.now(timezone.utc)
        result = self.session.execute(
            update(ActionPlanModel)
            .where(
                ActionPlanModel.id == plan_id,
                ActionPlanModel.status
                == ActionPlanStatus.PENDING_APPROVAL.value,
            )
            .values(
                status=ActionPlanStatus.APPROVED.value,
                approved_by=actor,
                approved_at=now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            self._raise_transition_error(plan_id)
        self.session.commit()
        return self.get(plan_id)

    def reject(self, plan_id: str, actor: str) -> ActionPlanModel:
        now = datetime.now(timezone.utc)
        result = self.session.execute(
            update(ActionPlanModel)
            .where(
                ActionPlanModel.id == plan_id,
                ActionPlanModel.status
                == ActionPlanStatus.PENDING_APPROVAL.value,
            )
            .values(
                status=ActionPlanStatus.REJECTED.value,
                approved_by=actor,
                approved_at=now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            self._raise_transition_error(plan_id)
        self.session.commit()
        return self.get(plan_id)

    def claim_for_execution(self, plan_id: str) -> ActionPlanModel:
        now = datetime.now(timezone.utc)
        result = self.session.execute(
            update(ActionPlanModel)
            .where(
                ActionPlanModel.id == plan_id,
                ActionPlanModel.status == ActionPlanStatus.APPROVED.value,
            )
            .values(
                status=ActionPlanStatus.EXECUTING.value,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            self._raise_transition_error(plan_id)
        self.session.commit()
        return self.get(plan_id)

    def mark_action_executing(self, action_id: str):
        now = datetime.now(timezone.utc)
        result = self.session.execute(
            update(ActionExecutionModel)
            .where(
                ActionExecutionModel.action_id == action_id,
                ActionExecutionModel.status
                == ActionExecutionStatus.PENDING.value,
            )
            .values(
                status=ActionExecutionStatus.EXECUTING.value,
                attempts=ActionExecutionModel.attempts + 1,
                started_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise InvalidStateTransitionError(
                "Action이 이미 실행됐거나 실행 중입니다."
            )
        self.session.commit()

    def complete_action(
        self,
        action_id: str,
        *,
        success: bool,
        provider: str,
        external_resource_id: str | None = None,
        latency_ms: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ):
        now = datetime.now(timezone.utc)
        self.session.execute(
            update(ActionExecutionModel)
            .where(
                ActionExecutionModel.action_id == action_id,
                ActionExecutionModel.status
                == ActionExecutionStatus.EXECUTING.value,
            )
            .values(
                status=(
                    ActionExecutionStatus.SUCCEEDED.value
                    if success
                    else ActionExecutionStatus.FAILED.value
                ),
                provider=provider,
                external_resource_id=external_resource_id,
                latency_ms=latency_ms,
                error_code=error_code,
                error_message=error_message,
                finished_at=now,
            )
        )
        self.session.commit()

    def finish_plan(self, plan_id: str) -> ActionPlanModel:
        plan = self.get(plan_id)
        success_count = sum(
            action.status == ActionExecutionStatus.SUCCEEDED.value
            for action in plan.actions
        )
        failure_count = sum(
            action.status == ActionExecutionStatus.FAILED.value
            for action in plan.actions
        )
        if success_count == len(plan.actions):
            status = ActionPlanStatus.SUCCEEDED
        elif failure_count == len(plan.actions):
            status = ActionPlanStatus.FAILED
        else:
            status = ActionPlanStatus.PARTIALLY_SUCCEEDED

        now = datetime.now(timezone.utc)
        self.session.execute(
            update(ActionPlanModel)
            .where(
                ActionPlanModel.id == plan_id,
                ActionPlanModel.status == ActionPlanStatus.EXECUTING.value,
            )
            .values(status=status.value, updated_at=now)
        )
        self.session.commit()
        return self.get(plan_id)

    def _raise_transition_error(self, plan_id: str):
        plan = self.session.get(ActionPlanModel, plan_id)
        if not plan:
            raise ActionPlanNotFoundError("Action Plan을 찾을 수 없습니다.")
        raise InvalidStateTransitionError(
            f"현재 상태({plan.status})에서는 요청한 작업을 수행할 수 없습니다."
        )
