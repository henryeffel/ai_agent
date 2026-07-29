from functools import lru_cache

from pydantic import TypeAdapter

from ieum.database import get_session_factory, init_database
from ieum.models.action_plan import ActionPlanModel
from ieum.providers.productivity import get_productivity_provider
from ieum.providers.productivity.base import ProductivityProviderError
from ieum.providers.llm import get_llm_provider
from ieum.providers.vector_search import get_vector_search_provider
from ieum.repositories.action_plan import ActionPlanRepository
from ieum.schemas.action_plan import (
    ActionExecutionResponse,
    ActionPlanCreate,
    ActionPlanResponse,
    GroundedActionPlanCreate,
)
from ieum.schemas.productivity import (
    CalendarPayload,
    EmailPayload,
    ProductivityPayload,
    TodoPayload,
)


payload_adapter = TypeAdapter(ProductivityPayload)


class InsufficientEvidenceError(RuntimeError):
    pass


class ActionWorkflowService:
    def __init__(self):
        init_database()
        self.session_factory = get_session_factory()

    def create_plan(self, request: ActionPlanCreate) -> ActionPlanResponse:
        with self.session_factory() as session:
            plan = ActionPlanRepository(session).create(request)
            return self._to_response(plan)

    def create_grounded_plan(
        self,
        request: GroundedActionPlanCreate,
    ) -> ActionPlanResponse:
        llm_provider = get_llm_provider()
        analysis = llm_provider.analyze_meeting(request.transcript)
        query = " ".join(
            [
                analysis.summary,
                *analysis.decisions,
                *(item.task for item in analysis.action_items),
            ]
        )
        hits = get_vector_search_provider().search(
            query,
            category=request.category,
            top_k=request.top_k,
            min_score=request.min_score,
        )
        if not hits:
            raise InsufficientEvidenceError(
                "실행 계획을 뒷받침할 조직 문서 근거가 부족합니다."
            )
        actions = llm_provider.generate_grounded_actions(analysis, hits)
        if not actions:
            raise InsufficientEvidenceError(
                "검색 근거로 생성할 수 있는 안전한 실행 작업이 없습니다."
            )
        return self.create_plan(
            ActionPlanCreate(
                meeting_id=request.meeting_id,
                evidence_chunk_ids=[hit.chunk_id for hit in hits],
                actions=actions,
            )
        )

    def get_plan(self, plan_id: str) -> ActionPlanResponse:
        with self.session_factory() as session:
            plan = ActionPlanRepository(session).get(plan_id)
            return self._to_response(plan)

    def approve_plan(self, plan_id: str, actor: str) -> ActionPlanResponse:
        with self.session_factory() as session:
            plan = ActionPlanRepository(session).approve(plan_id, actor)
            return self._to_response(plan)

    def reject_plan(self, plan_id: str, actor: str) -> ActionPlanResponse:
        with self.session_factory() as session:
            plan = ActionPlanRepository(session).reject(plan_id, actor)
            return self._to_response(plan)

    def execute_plan(self, plan_id: str) -> ActionPlanResponse:
        provider = get_productivity_provider()
        with self.session_factory() as session:
            repository = ActionPlanRepository(session)
            plan = repository.claim_for_execution(plan_id)

            for action in plan.actions:
                repository.mark_action_executing(action.action_id)
                payload = payload_adapter.validate_python(action.payload)
                try:
                    result = self._execute_tool(
                        provider,
                        action.action_id,
                        payload,
                    )
                    repository.complete_action(
                        action.action_id,
                        success=result.success,
                        provider=result.provider,
                        external_resource_id=result.external_resource_id,
                        latency_ms=result.latency_ms,
                        error_code=result.error_code,
                        error_message=result.error_message,
                    )
                except ProductivityProviderError as exc:
                    repository.complete_action(
                        action.action_id,
                        success=False,
                        provider=provider.provider_name,
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                except Exception:
                    repository.complete_action(
                        action.action_id,
                        success=False,
                        provider=provider.provider_name,
                        error_code="internal_error",
                        error_message="Tool 실행 중 내부 오류가 발생했습니다.",
                    )

            return self._to_response(repository.finish_plan(plan_id))

    @staticmethod
    def _execute_tool(provider, action_id, payload):
        if isinstance(payload, CalendarPayload):
            return provider.create_calendar_event(action_id, payload)
        if isinstance(payload, TodoPayload):
            return provider.create_todo(action_id, payload)
        if isinstance(payload, EmailPayload):
            return provider.send_email(action_id, payload)
        raise RuntimeError("지원하지 않는 Productivity Tool입니다.")

    @staticmethod
    def _to_response(plan: ActionPlanModel) -> ActionPlanResponse:
        return ActionPlanResponse(
            id=plan.id,
            meeting_id=plan.meeting_id,
            evidence_chunk_ids=plan.evidence_chunk_ids,
            status=plan.status,
            approved_by=plan.approved_by,
            approved_at=plan.approved_at,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            actions=[
                ActionExecutionResponse(
                    id=action.id,
                    action_id=action.action_id,
                    tool=action.tool,
                    payload=action.payload,
                    status=action.status,
                    attempts=action.attempts,
                    provider=action.provider,
                    external_resource_id=action.external_resource_id,
                    latency_ms=action.latency_ms,
                    error_code=action.error_code,
                    error_message=action.error_message,
                )
                for action in plan.actions
            ],
        )


@lru_cache
def get_action_workflow_service() -> ActionWorkflowService:
    return ActionWorkflowService()
