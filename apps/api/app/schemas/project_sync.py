from datetime import datetime
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


class SyncJobCreatedResponse(BaseModel):
    job_id: UUID
    project_id: UUID
    status: str


class SyncJobStatusResponse(BaseModel):
    job_id: UUID
    project_id: UUID
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: ProjectSyncResponse | None = None