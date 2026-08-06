import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ieum.api.routers import action_plans, health, knowledge, meetings
from ieum.config import get_settings
from ieum.observability import configure_logging, log_event, request_context
from ieum.api.errors import install_error_handlers


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


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    application = FastAPI(title="IEUM Meeting-to-Action Agent")
    install_error_handlers(application)

    @application.middleware("http")
    async def request_observability(request: Request, call_next):
        supplied_id = request.headers.get("X-Request-ID", "").strip()
        request_id = supplied_id[:100] if supplied_id else str(uuid4())
        started_at = time.perf_counter()
        with request_context(request_id):
            try:
                response = await call_next(request)
            except Exception:
                log_event(
                    logging.getLogger("ieum.request"),
                    "request_failed",
                    level=logging.ERROR,
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    latency_ms=max(1, int((time.perf_counter() - started_at) * 1000)),
                    error_code="internal_error",
                )
                raise
            response.headers["X-Request-ID"] = request_id
            log_event(
                logging.getLogger("ieum.request"),
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=max(1, int((time.perf_counter() - started_at) * 1000)),
            )
            return response
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(meetings.router)
    application.include_router(knowledge.router)
    application.include_router(action_plans.router)

    @application.get("/openapi/copilot.json", include_in_schema=False)
    def copilot_openapi():
        schema = application.openapi()
        allowed_paths = {
            "/api/v1/meetings/analyze",
            "/api/v1/action-plans/grounded",
            "/api/v1/action-plans/{plan_id}",
            "/api/v1/action-plans/{plan_id}/approve",
            "/api/v1/action-plans/{plan_id}/execute",
        }
        return {
            **schema,
            "info": {
                **schema["info"],
                "title": "IEUM Copilot Actions",
                "description": "Meeting analysis, grounded planning, human approval, and explicit execution actions for connector import.",
            },
            "paths": {
                path: operations
                for path, operations in schema["paths"].items()
                if path in allowed_paths
            },
        }

    if settings.app_mode == "azure":
        # Importing this module initializes Azure clients, so it must never happen
        # in the reproducible mock mode.
        from ieum.api.routers.legacy_azure import app as legacy_app

        for route in legacy_app.routes:
            if getattr(route, "path", None) in LEGACY_PATHS:
                application.router.routes.append(route)
    return application


app = create_app()
