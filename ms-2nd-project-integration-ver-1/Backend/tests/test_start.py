import sys

from ieum import start


def test_demo_start_runs_migration_seed_and_uvicorn(monkeypatch):
    module_calls = []
    exec_call = {}

    monkeypatch.setenv("APP_MODE", "demo")
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setattr(start, "run_module", lambda *args: module_calls.append(args))
    monkeypatch.setattr(
        start.os,
        "execv",
        lambda executable, args: exec_call.update(
            executable=executable,
            args=args,
        ),
    )

    start.main()

    assert module_calls == [
        ("alembic", "upgrade", "head"),
        ("ieum.demo", "seed"),
    ]
    assert exec_call["executable"] == sys.executable
    assert exec_call["args"][-2:] == ["--port", "10000"]


def test_non_demo_start_skips_seed(monkeypatch):
    module_calls = []
    monkeypatch.setenv("APP_MODE", "mock")
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(start, "run_module", lambda *args: module_calls.append(args))
    monkeypatch.setattr(start.os, "execv", lambda *_: None)

    start.main()

    assert module_calls == [("alembic", "upgrade", "head")]
