from typing import Annotated

from fastapi import Header, HTTPException

from ieum.config import get_settings
from ieum.security.identity import ActorContext
from ieum.security.mock_identity import build_mock_actor


def get_actor_context(
    subject_id: Annotated[str, Header(alias="X-Actor-Id")] = "mock-user",
    email: Annotated[str | None, Header(alias="X-Actor-Email")] = "mock.user@example.com",
    roles: Annotated[str, Header(alias="X-Actor-Roles")] = "approver,executor",
) -> ActorContext:
    app_mode = get_settings().app_mode
    if app_mode == "demo":
        return build_mock_actor(
            subject_id="public-demo-user",
            email="demo.user@example.com",
            roles="approver,executor",
        )
    if app_mode != "mock":
        raise HTTPException(
            status_code=501,
            detail="Entra ID token validation is not configured.",
        )
    return build_mock_actor(
        subject_id=subject_id,
        email=email,
        roles=roles,
    )
