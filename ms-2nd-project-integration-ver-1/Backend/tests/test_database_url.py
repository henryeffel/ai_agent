from ieum.database import normalize_database_url


def test_generic_postgresql_url_uses_psycopg_3():
    assert normalize_database_url(
        "postgresql://postgres:secret@db.example.com/postgres"
    ) == "postgresql+psycopg://postgres:secret@db.example.com/postgres"


def test_legacy_postgres_url_uses_psycopg_3():
    assert normalize_database_url(
        "postgres://postgres:secret@db.example.com/postgres"
    ) == "postgresql+psycopg://postgres:secret@db.example.com/postgres"


def test_explicit_driver_and_sqlite_urls_are_unchanged():
    psycopg_url = "postgresql+psycopg://postgres:secret@db.example.com/postgres"
    sqlite_url = "sqlite:///ieum.db"

    assert normalize_database_url(psycopg_url) == psycopg_url
    assert normalize_database_url(sqlite_url) == sqlite_url
