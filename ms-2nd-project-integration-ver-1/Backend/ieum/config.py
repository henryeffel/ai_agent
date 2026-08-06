import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_mode: str
    allowed_origins: tuple[str, ...]


def get_settings() -> Settings:
    app_mode = os.getenv("APP_MODE", "mock").lower()
    if app_mode not in {"mock", "demo", "azure"}:
        raise RuntimeError("APP_MODE는 mock, demo 또는 azure여야 합니다.")
    if app_mode == "demo":
        required = {
            "LLM_PROVIDER": "nvidia",
            "EMBEDDING_PROVIDER": "nvidia",
            "VECTOR_SEARCH_PROVIDER": "pgvector",
            "PRODUCTIVITY_PROVIDER": "mock",
        }
        invalid = {
            key: os.getenv(key, "").lower()
            for key, expected in required.items()
            if os.getenv(key, "").lower() != expected
        }
        if invalid:
            expected_text = ", ".join(
                f"{key}={value}" for key, value in required.items()
            )
            raise RuntimeError(
                "demo 모드는 안전한 공개 배포 Provider 조합이 필요합니다: "
                f"{expected_text}"
            )
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url.startswith("postgresql"):
            raise RuntimeError(
                "demo 모드는 PostgreSQL DATABASE_URL이 필요합니다."
            )
    origins = tuple(
        value.strip()
        for value in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:5174",
        ).split(",")
        if value.strip()
    )
    return Settings(app_mode=app_mode, allowed_origins=origins)
