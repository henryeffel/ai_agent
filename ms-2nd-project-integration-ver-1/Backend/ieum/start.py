"""Container entrypoint that does not depend on shell command parsing."""

import os
import subprocess
import sys


def run_module(*arguments: str) -> None:
    subprocess.run([sys.executable, "-m", *arguments], check=True)


def main() -> None:
    run_module("alembic", "upgrade", "head")
    if os.getenv("APP_MODE", "mock").lower() == "demo":
        run_module("ieum.demo", "seed")

    port = os.getenv("PORT", "8000")
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
    )


if __name__ == "__main__":
    main()
