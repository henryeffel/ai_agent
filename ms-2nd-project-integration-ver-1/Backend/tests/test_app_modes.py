import os
import subprocess
import sys

from main import app


LEGACY_PATHS = {
    "/files",
    "/dashboard-data",
    "/upload",
    "/chat",
    "/execute-action",
    "/approve-calendar",
    "/create-outlook-task",
    "/delete",
    "/generate-minutes",
}


def test_mock_mode_registers_workflow_routes_only():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/meetings/analyze" in paths
    assert "/analyze-meeting" in paths
    assert "/api/v1/action-plans/{plan_id}/execute" in paths
    assert paths.isdisjoint(LEGACY_PATHS)


def test_mock_mode_does_not_import_legacy_azure_application():
    env = os.environ.copy()
    env["APP_MODE"] = "mock"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, main; assert 'ieum.api.routers.legacy_azure' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
