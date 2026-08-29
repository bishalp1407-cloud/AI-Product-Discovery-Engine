from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
)
from app.models.feedback_source import FeedbackSource
from app.models.insight import Insight
from app.models.insight_feedback import InsightFeedback


@dataclass(frozen=True)
class InsightEvidence:
    feedback_id: UUID
    source_type: str
    raw_text: str
    severity: str | None
    sentiment: str | None


@dataclass(frozen=True)
class SourceBreakdown:
    source_type: str
    evidence_count: int


@dataclass(frozen=True)
class InsightDetail:
    id: UUID
    project_id: UUID
    title: str
    category: str
    description: str | None
    feedback_count: int
    reach: float
    impact: float
    confidence: float
    opportunity_score: float
    source_breakdown: list[SourceBreakdown]
    evidence: list[InsightEvidence]


def _enum_value(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)

    if enum_value is not None:
        return str(enum_value)

    return str(value)


def get_insight_detail(
    db: Session,
    *,
    project_id: UUID,
    insight_id: UUID,
) -> InsightDetail | None:
    insight = db.scalar(
        select(Insight).where(
            Insight.id == insight_id,
            Insight.project_id == project_id,
        )
    )

    if insight is None:
        return None

    rows = db.execute(
        select(
            Feedback.id,
            Feedback.raw_text,
            FeedbackSource.source_type,
            FeedbackAnalysis.severity,
            FeedbackAnalysis.sentiment,
        )
        .join(
            InsightFeedback,
            InsightFeedback.feedback_id == Feedback.id,
        )
        .join(
            FeedbackSource,
            FeedbackSource.id == Feedback.source_id,
        )
        .outerjoin(
    FeedbackAnalysis,
    (
        (FeedbackAnalysis.feedback_id == Feedback.id)
        & (FeedbackAnalysis.prompt_version == "v3")
        & (
            FeedbackAnalysis.analysis_status
            == AnalysisStatus.COMPLETED
        )
    ),
)
        .where(
            InsightFeedback.insight_id == insight_id,
            Feedback.project_id == project_id,
        )
        .order_by(Feedback.created_at.asc())
    ).all()

    evidence = [
        InsightEvidence(
            feedback_id=row[0],
            raw_text=row[1],
            source_type=_enum_value(row[2]) or "unknown",
            severity=_enum_value(row[3]),
            sentiment=_enum_value(row[4]),
        )
        for row in rows
    ]

    breakdown_rows = db.execute(
        select(
            FeedbackSource.source_type,
            func.count(Feedback.id),
        )
        .join(
            Feedback,
            Feedback.source_id == FeedbackSource.id,
        )
        .join(
            InsightFeedback,
            InsightFeedback.feedback_id == Feedback.id,
        )
        .where(
            InsightFeedback.insight_id == insight_id,
            Feedback.project_id == project_id,
        )
        .group_by(FeedbackSource.source_type)
        .order_by(func.count(Feedback.id).desc())
    ).all()

    source_breakdown = [
        SourceBreakdown(
            source_type=_enum_value(row[0]) or "unknown",
            evidence_count=row[1],
        )
        for row in breakdown_rows
    ]

    return InsightDetail(
        id=insight.id,
        project_id=insight.project_id,
        title=insight.title,
        category=insight.category,
        description=insight.description,
        feedback_count=insight.feedback_count,
        reach=insight.reach_score,
        impact=insight.impact_score,
        confidence=insight.confidence_score,
        opportunity_score=insight.opportunity_score,
        source_breakdown=source_breakdown,
        evidence=evidence,
    )