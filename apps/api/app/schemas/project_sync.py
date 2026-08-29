from uuid import UUID

from pydantic import BaseModel, Field


class SourceSyncResponse(BaseModel):
    source_id: UUID
    source_name: str
    source_type: str
    fetched: int = Field(ge=0)
    created: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    error: str | None = None


class ProjectSyncResponse(BaseModel):
    project_id: UUID
    sources_synced: int = Field(ge=0)
    feedback_fetched: int = Field(ge=0)
    feedback_created: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    analyses_completed: int = Field(ge=0)
    analyses_failed: int = Field(ge=0)
    insights_created: int = Field(ge=0)
    sources: list[SourceSyncResponse]