from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ActorContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    tenant_id: str | None = Field(default=None, max_length=200)
    roles: set[str] = Field(default_factory=set)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    @property
    def audit_id(self) -> str:
        return str(self.email) if self.email else self.subject_id
