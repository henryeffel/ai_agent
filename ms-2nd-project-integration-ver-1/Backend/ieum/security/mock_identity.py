from ieum.security.identity import ActorContext


def build_mock_actor(
    *,
    subject_id: str,
    email: str | None,
    roles: str,
) -> ActorContext:
    return ActorContext(
        subject_id=subject_id,
        email=email,
        tenant_id="mock-tenant",
        roles={role.strip() for role in roles.split(",") if role.strip()},
    )
