from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ieum.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ActionPlanModel(Base):
    __tablename__ = "action_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(100), index=True)
    evidence_chunk_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(40), index=True)
    approved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    actions: Mapped[list["ActionExecutionModel"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ActionExecutionModel.created_at",
        lazy="selectin",
    )


class ActionExecutionModel(Base):
    __tablename__ = "action_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    action_plan_id: Mapped[str] = mapped_column(
        ForeignKey("action_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_resource_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    plan: Mapped[ActionPlanModel] = relationship(back_populates="actions")
