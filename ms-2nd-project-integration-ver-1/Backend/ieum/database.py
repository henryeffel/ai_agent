import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./ieum.db")
    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )
    return create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory():
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        expire_on_commit=False,
    )


def init_database():
    # Import model modules before create_all so metadata contains every table.
    from ieum.models import action_plan  # noqa: F401

    Base.metadata.create_all(get_engine())
