from uuid import uuid4

from ieum.providers.llm.base import LLMProvider
from ieum.schemas.action_plan import ActionCreate
from ieum.schemas.knowledge import KnowledgeSearchHit
from ieum.schemas.meeting import ActionItem, MeetingAnalysis
from ieum.schemas.productivity import TodoPayload


class MockLLMProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-meeting-analyzer-v1"

    def analyze_meeting(self, transcript: str) -> MeetingAnalysis:
        preview = " ".join(transcript.split())[:180]
        return MeetingAnalysis(
            summary=f"Mock 분석 결과: {preview}",
            decisions=["Mock Mode에서 회의 분석 Workflow를 검증합니다."],
            action_items=[
                ActionItem(
                    task="회의 후속 작업을 검토합니다.",
                    assignee=None,
                    due_date=None,
                )
            ],
            open_issues=["실제 LLM 분석은 NVIDIA Provider에서 수행합니다."],
        )

    def generate_grounded_actions(
        self,
        analysis: MeetingAnalysis,
        evidence: list[KnowledgeSearchHit],
    ) -> list[ActionCreate]:
        if not evidence:
            return []
        return [
            ActionCreate(
                action_id=f"todo-{uuid4()}",
                payload=TodoPayload(
                    title=item.task,
                    due_at=(
                        f"{item.due_date.isoformat()}T18:00:00+09:00"
                        if item.due_date
                        else None
                    ),
                    description=(
                        f"RAG 근거: {', '.join(hit.chunk_id for hit in evidence)}"
                    ),
                ),
            )
            for item in analysis.action_items
        ]
