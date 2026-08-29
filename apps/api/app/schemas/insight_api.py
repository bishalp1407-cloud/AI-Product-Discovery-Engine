from uuid import UUID

from pydantic import BaseModel, Field


class InsightListItem(BaseModel):
    id: UUID
    rank: int = Field(ge=1)

    title: str
    category: str
    description: str | None

    feedback_count: int = Field(ge=0)

    reach: float = Field(ge=0)
    impact: float = Field(ge=0)
    confidence: float = Field(ge=0)
    opportunity_score: float = Field(ge=0)


class InsightListResponse(BaseModel):
    project_id: UUID

    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

    items: list[InsightListItem]

class InsightEvidenceItem(BaseModel):
    feedback_id: UUID
    source_type: str
    raw_text: str
    severity: str | None
    sentiment: str | None


class InsightSourceBreakdown(BaseModel):
    source_type: str
    evidence_count: int = Field(ge=0)


class InsightDetailResponse(BaseModel):
    id: UUID
    project_id: UUID

    title: str
    category: str
    description: str | None

    feedback_count: int = Field(ge=0)

    reach: float = Field(ge=0)
    impact: float = Field(ge=0)
    confidence: float = Field(ge=0)
    opportunity_score: float = Field(ge=0)

    source_breakdown: list[InsightSourceBreakdown]
    evidence: list[InsightEvidenceItem]