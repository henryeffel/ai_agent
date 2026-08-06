import json
import logging
from datetime import datetime, timezone
from typing import Any

from ieum.observability.context import get_request_id


ALLOWED_FIELDS = {
    "request_id",
    "plan_id",
    "action_id",
    "meeting_id",
    "provider",
    "tool",
    "status",
    "latency_ms",
    "error_code",
    "method",
    "path",
    "status_code",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        event_data = getattr(record, "event_data", {})
        payload.update(
            {
                key: value
                for key, value in event_data.items()
                if key in ALLOWED_FIELDS and value is not None
            }
        )
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger("ieum")
    logger.setLevel(level)
    if any(getattr(handler, "_ieum_json", False) for handler in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler._ieum_json = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.propagate = False


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    safe_fields = {key: value for key, value in fields.items() if key in ALLOWED_FIELDS}
    safe_fields.setdefault("request_id", get_request_id())
    logger.log(level, event, extra={"event_data": safe_fields})


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, domain = value.split("@", 1)
    visible = local[:1]
    return f"{visible}{'*' * max(3, len(local) - 1)}@{domain}"
