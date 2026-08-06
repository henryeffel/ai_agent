from fastapi.testclient import TestClient

from main import app


client = TestClient(app)

EXPECTED_OPERATIONS = {
    "/api/v1/meetings/analyze": "analyzeMeeting",
    "/api/v1/action-plans/grounded": "createGroundedActionPlan",
    "/api/v1/action-plans/{plan_id}": "getActionPlan",
    "/api/v1/action-plans/{plan_id}/approve": "approveActionPlan",
    "/api/v1/action-plans/{plan_id}/execute": "executeApprovedActionPlan",
}


def test_copilot_schema_contains_only_supported_actions():
    response = client.get("/openapi/copilot.json")

    assert response.status_code == 200
    schema = response.json()
    assert set(schema["paths"]) == set(EXPECTED_OPERATIONS)
    assert schema["info"]["title"] == "IEUM Copilot Actions"


def test_copilot_operations_have_stable_ids_and_descriptions():
    schema = client.get("/openapi/copilot.json").json()

    for path, operation_id in EXPECTED_OPERATIONS.items():
        methods = schema["paths"][path]
        operation = methods["get"] if "get" in methods else methods["post"]
        assert operation["operationId"] == operation_id
        assert operation["summary"]
        assert operation["description"]


def test_error_responses_reference_common_error_schema():
    schema = client.get("/openapi/copilot.json").json()
    operation = schema["paths"]["/api/v1/action-plans/{plan_id}/execute"]["post"]

    for status in ("403", "404", "409", "422", "502", "504"):
        response_schema = operation["responses"][status]["content"]["application/json"]["schema"]
        assert response_schema["$ref"].endswith("/ErrorResponse")


def test_validation_errors_use_connector_safe_envelope():
    response = client.post(
        "/api/v1/meetings/analyze",
        json={"transcript": "짧음"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["retryable"] is False
    assert body["error"]["details"]["fields"]
