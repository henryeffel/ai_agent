import json
import os
import subprocess
import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[3]
FRONTEND = REPOSITORY / "ms-2nd-project-integration-ver-1"


def test_render_blueprint_uses_demo_mode_and_secret_placeholders():
    blueprint = (REPOSITORY / "render.yaml").read_text(encoding="utf-8")

    assert "APP_MODE\n        value: demo" in blueprint
    assert "PRODUCTIVITY_PROVIDER\n        value: mock" in blueprint
    assert "dockerCommand: python -m ieum.start" in blueprint
    assert 'dockerCommand: sh -c "' not in blueprint
    assert "&&" not in blueprint
    for secret in ("DATABASE_URL", "NVIDIA_API_KEY", "ALLOWED_ORIGINS"):
        assert f"key: {secret}\n        sync: false" in blueprint


def test_vercel_config_builds_vite_spa():
    config = json.loads((FRONTEND / "vercel.json").read_text(encoding="utf-8"))

    assert config["framework"] == "vite"
    assert config["outputDirectory"] == "dist"
    assert config["rewrites"] == [
        {"source": "/(.*)", "destination": "/index.html"}
    ]


def test_supabase_verification_requires_destructive_confirmation():
    environment = os.environ.copy()
    environment["DATABASE_URL"] = "postgresql+psycopg://example.invalid/ieum"
    result = subprocess.run(
        [sys.executable, "scripts/verify_supabase.py"],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode != 0
    assert "--confirm-empty-database" in result.stderr
