import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select

from ieum.ingestion import DocumentMetadata, chunk_document
from ieum.models.action_plan import ActionExecutionModel, ActionPlanModel


DEFAULT_SEED_PATH = Path(__file__).with_name("seed_knowledge.json")


class DemoMaintenanceService:
    def __init__(self, vector_provider, session_factory):
        self.vector_provider = vector_provider
        self.session_factory = session_factory

    def seed_knowledge(self, path: Path = DEFAULT_SEED_PATH) -> int:
        documents = json.loads(path.read_text(encoding="utf-8"))
        chunks = []
        for document in documents:
            chunks.extend(
                chunk_document(
                    document["content"],
                    DocumentMetadata(
                        document_id=document["document_id"],
                        title=document["title"],
                        category=document["category"],
                        source_url=f"demo://{document['document_id']}",
                        updated_at=document.get("updated_at"),
                    ),
                    max_chars=800,
                )
            )
        return self.vector_provider.index_chunks(chunks)

    def cleanup_plans(
        self,
        *,
        older_than_hours: int,
        now: datetime | None = None,
    ) -> int:
        if older_than_hours < 1:
            raise ValueError("older_than_hours는 1 이상이어야 합니다.")
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(
            hours=older_than_hours
        )
        plan_ids = select(ActionPlanModel.id).where(
            ActionPlanModel.meeting_id.like("demo-%"),
            ActionPlanModel.created_at < cutoff,
        )
        with self.session_factory() as session:
            session.execute(
                delete(ActionExecutionModel).where(
                    ActionExecutionModel.action_plan_id.in_(plan_ids)
                )
            )
            result = session.execute(
                delete(ActionPlanModel).where(
                    ActionPlanModel.meeting_id.like("demo-%"),
                    ActionPlanModel.created_at < cutoff,
                )
            )
            session.commit()
            return result.rowcount or 0
