from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DistributionItem(BaseModel):
    name: str
    count: int = Field(ge=0)


class SourceAnalyticsItem(BaseModel):
    source_type: str
    count: int = Field(ge=0)


class FeedbackTrendItem(BaseModel):
    date: date
    count: int = Field(ge=0)


class RecentFeedbackItem(BaseModel):
    feedback_id: UUID
    source_type: str
    raw_text: str
    sentiment: str | None
    category: str | None
    severity: str | None
    source_created_at: datetime | None


class ProjectAnalyticsResponse(BaseModel):
    project_id: UUID
    relevant_feedback: int = Field(ge=0)

    sentiment_distribution: list[DistributionItem]
    category_distribution: list[DistributionItem]
    source_breakdown: list[SourceAnalyticsItem]
    feedback_trend: list[FeedbackTrendItem]
    recent_feedback: list[RecentFeedbackItem]