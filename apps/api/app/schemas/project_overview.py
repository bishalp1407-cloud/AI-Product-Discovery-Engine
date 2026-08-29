from uuid import UUID

from pydantic import BaseModel, Field


class ProjectOverviewResponse(BaseModel):
    project_id: UUID
    project_name: str

    total_feedback: int = Field(ge=0)
    relevant_feedback: int = Field(ge=0)
    source_count: int = Field(ge=0)
    insight_count: int = Field(ge=0)