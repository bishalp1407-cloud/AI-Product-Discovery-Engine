from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.insight import Insight


@dataclass(frozen=True)
class RankedInsight:
    id: UUID
    rank: int
    title: str
    category: str
    description: str | None
    feedback_count: int
    reach: float
    impact: float
    confidence: float
    opportunity_score: float


@dataclass(frozen=True)
class RankedInsightPage:
    project_id: UUID
    total: int
    limit: int
    offset: int
    items: list[RankedInsight]


def get_ranked_insights(
    db: Session,
    *,
    project_id: UUID,
    limit: int,
    offset: int,
) -> RankedInsightPage:
    total = db.scalar(
        select(func.count(Insight.id))
        .where(Insight.project_id == project_id)
    ) or 0

    insights = db.scalars(
        select(Insight)
        .where(Insight.project_id == project_id)
        .order_by(
            Insight.opportunity_score.desc(),
            Insight.created_at.asc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    items = [
        RankedInsight(
            id=insight.id,
            rank=offset + index + 1,
            title=insight.title,
            category=insight.category,
            description=insight.description,
            feedback_count=insight.feedback_count,
            reach=insight.reach_score,
            impact=insight.impact_score,
            confidence=insight.confidence_score,
            opportunity_score=insight.opportunity_score,
        )
        for index, insight in enumerate(insights)
    ]

    return RankedInsightPage(
        project_id=project_id,
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
