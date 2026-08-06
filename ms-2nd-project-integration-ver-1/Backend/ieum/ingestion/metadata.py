from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(default="reference", min_length=1, max_length=50)
    source_url: str | None = Field(default=None, max_length=2000)
    created_at: datetime | None = None
    updated_at: datetime | None = None
