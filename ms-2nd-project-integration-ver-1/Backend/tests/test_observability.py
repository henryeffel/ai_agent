import json
import logging

from fastapi.testclient import TestClient

from ieum.observability.logging import JsonFormatter, mask_email
from main import app


client = TestClient(app)


def test_request_id_is_preserved_in_response():
    response = client.get(
        "/health/live",
        headers={"X-Request-ID": "trace-test-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-test-123"


def test_request_id_is_generated_when_missing():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_json_formatter_only_emits_allowlisted_fields():
    record = logging.LogRecord(
        name="ieum.action",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="action_execution_completed",
        args=(),
        exc_info=None,
    )
    record.event_data = {
        "request_id": "request-1",
        "plan_id": "plan-1",
        "status": "SUCCEEDED",
        "transcript": "절대로 로그에 남으면 안 되는 회의 전문",
        "secret": "signed-url-secret",
        "email": "private@example.com",
    }

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "request-1"
    assert payload["plan_id"] == "plan-1"
    assert "transcript" not in payload
    assert "secret" not in payload
    assert "email" not in payload
    assert "private@example.com" not in json.dumps(payload)


def test_email_masking_keeps_domain_but_hides_local_part():
    assert mask_email("henry@example.com") == "h****@example.com"
