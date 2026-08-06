import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def normalize_database_url(database_url: str) -> str:
    """Select psycopg 3 when a provider returns a generic Postgres URL."""
    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )
    return database_url


@lru_cache
def get_engine():
    database_url = normalize_database_url(
        os.getenv("DATABASE_URL", "sqlite:///./ieum.db")
    )
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
