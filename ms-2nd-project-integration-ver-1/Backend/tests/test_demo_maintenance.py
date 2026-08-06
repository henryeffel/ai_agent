from datetime import datetime, timedelta, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from ieum.database import get_engine, get_session_factory
from ieum.demo.maintenance import DemoMaintenanceService
from ieum.models.action_plan import ActionExecutionModel, ActionPlanModel
from ieum.providers.embedding.mock import MockEmbeddingProvider
from ieum.providers.vector_search.mock import MockVectorSearchProvider


def test_seed_is_idempotent_and_contains_stable_demo_metadata():
    provider = MockVectorSearchProvider(MockEmbeddingProvider())
    service = DemoMaintenanceService(provider, lambda: None)

    first_count = service.seed_knowledge()
    first_ids = set(provider._chunks)
    second_count = service.seed_knowledge()

    assert first_count == second_count == 10
    assert set(provider._chunks) == first_ids
    assert len(provider._chunks) == 10
    assert all(chunk_id.startswith("demo-") for chunk_id in first_ids)
    assert all(
        chunk.source_url.startswith("demo://")
        for chunk, vector in provider._chunks.values()
    )


def test_cleanup_deletes_only_expired_demo_plans(tmp_path, monkeypatch):
    database_path = tmp_path / "demo-cleanup.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    now = datetime.now(timezone.utc)

    with get_session_factory()() as session:
        session.add_all(
            [
                _plan("expired-demo", "demo-expired", now - timedelta(hours=30)),
                _plan("recent-demo", "demo-recent", now - timedelta(hours=1)),
                _plan("non-demo", "internal-record", now - timedelta(hours=30)),
            ]
        )
        session.commit()

    service = DemoMaintenanceService(None, get_session_factory())
    deleted = service.cleanup_plans(older_than_hours=24, now=now)

    with get_session_factory()() as session:
        remaining_plans = set(session.scalars(select(ActionPlanModel.id)))
        remaining_actions = set(session.scalars(select(ActionExecutionModel.id)))
    assert deleted == 1
    assert remaining_plans == {"recent-demo", "non-demo"}
    assert remaining_actions == {"recent-demo-action", "non-demo-action"}

    get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()


def _plan(plan_id, meeting_id, created_at):
    plan = ActionPlanModel(
        id=plan_id,
        meeting_id=meeting_id,
        evidence_chunk_ids=[],
        status="PENDING_APPROVAL",
        created_at=created_at,
        updated_at=created_at,
    )
    plan.actions.append(
        ActionExecutionModel(
            id=f"{plan_id}-action",
            action_id=f"{plan_id}-action-id",
            tool="todo",
            payload={"tool": "todo", "title": "Demo cleanup"},
            status="PENDING",
            attempts=0,
            created_at=created_at,
        )
    )
    return plan
