import argparse
import os
import subprocess
import sys


def run(*arguments):
    subprocess.run([sys.executable, *arguments], check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Verify IEUM migrations and pgvector against a dedicated Supabase database."
    )
    parser.add_argument(
        "--confirm-empty-database",
        action="store_true",
        help="Confirm that IEUM tables in this database may be dropped and recreated.",
    )
    args = parser.parse_args()
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        parser.error("PostgreSQL DATABASE_URL이 필요합니다.")
    if not args.confirm_empty_database:
        parser.error(
            "통합 테스트는 IEUM table을 downgrade/recreate합니다. "
            "비어 있는 전용 DB인지 확인한 뒤 --confirm-empty-database를 사용하세요."
        )

    os.environ.update(
        {
            "APP_MODE": "mock",
            "LLM_PROVIDER": "mock",
            "PRODUCTIVITY_PROVIDER": "mock",
            "EMBEDDING_PROVIDER": "mock",
            "MOCK_EMBEDDING_DIMENSION": "2048",
            "VECTOR_SEARCH_PROVIDER": "pgvector",
            "IEUM_INTEGRATION_DATABASE": "1",
        }
    )
    run("-m", "alembic", "upgrade", "head")
    run("-m", "alembic", "downgrade", "-1")
    run("-m", "alembic", "upgrade", "head")
    run("-m", "pytest", "-q", "tests/integration")
    print("supabase_postgres_verification=passed")


if __name__ == "__main__":
    main()
