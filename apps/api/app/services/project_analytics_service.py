from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
)
from app.models.feedback_source import FeedbackSource
from app.models.project import Project
from app.services.feedback_analysis_service import PROMPT_VERSION


@dataclass
class DistributionValue:
    name: str
    count: int


@dataclass
class SourceAnalytics:
    source_type: str
    count: int


@dataclass
class TrendValue:
    date: date
    count: int


@dataclass
class RecentFeedback:
    feedback_id: UUID
    source_type: str
    raw_text: str
    sentiment: str | None
    category: str | None
    severity: str | None
    source_created_at: datetime | None


@dataclass
class ProjectAnalytics:
    project_id: UUID
    relevant_feedback: int
    sentiment_distribution: list[DistributionValue]
    category_distribution: list[DistributionValue]
    source_breakdown: list[SourceAnalytics]
    feedback_trend: list[TrendValue]
    recent_feedback: list[RecentFeedback]


def _enum_value(value) -> str | None:
    if value is None:
        return None

    return getattr(value, "value", str(value))


def get_project_analytics(
    db: Session,
    *,
    project_id: UUID,
    days: int = 30,
    recent_limit: int = 10,
) -> ProjectAnalytics | None:
    project = db.get(Project, project_id)

    if project is None:
        return None

    base_filters = (
        Feedback.project_id == project_id,
        FeedbackAnalysis.prompt_version == PROMPT_VERSION,
        FeedbackAnalysis.analysis_status == AnalysisStatus.COMPLETED,
        FeedbackAnalysis.is_relevant.is_(True),
    )

    # ---------------------------------------------------------
    # Total relevant analyzed feedback
    # ---------------------------------------------------------

    relevant_feedback = db.execute(
        select(func.count(Feedback.id))
        .join(
            FeedbackAnalysis,
            FeedbackAnalysis.feedback_id == Feedback.id,
        )
        .where(*base_filters)
    ).scalar_one()

    # ---------------------------------------------------------
    # Sentiment distribution
    # ---------------------------------------------------------

    sentiment_rows = db.execute(
        select(
            FeedbackAnalysis.sentiment,
            func.count(Feedback.id),
        )
        .join(
            Feedback,
            Feedback.id == FeedbackAnalysis.feedback_id,
        )
        .where(*base_filters)
        .where(FeedbackAnalysis.sentiment.is_not(None))
        .group_by(FeedbackAnalysis.sentiment)
        .order_by(func.count(Feedback.id).desc())
    ).all()

    sentiment_distribution = [
        DistributionValue(
            name=_enum_value(sentiment),
            count=count,
        )
        for sentiment, count in sentiment_rows
    ]

    # ---------------------------------------------------------
    # Category distribution
    # ---------------------------------------------------------

    category_rows = db.execute(
        select(
            FeedbackAnalysis.category,
            func.count(Feedback.id),
        )
        .join(
            Feedback,
            Feedback.id == FeedbackAnalysis.feedback_id,
        )
        .where(*base_filters)
        .where(FeedbackAnalysis.category.is_not(None))
        .group_by(FeedbackAnalysis.category)
        .order_by(func.count(Feedback.id).desc())
    ).all()

    category_distribution = [
        DistributionValue(
            name=category,
            count=count,
        )
        for category, count in category_rows
    ]

    # ---------------------------------------------------------
    # Relevant feedback by source
    # ---------------------------------------------------------

    source_rows = db.execute(
        select(
            FeedbackSource.source_type,
            func.count(Feedback.id),
        )
        .join(
            Feedback,
            Feedback.source_id == FeedbackSource.id,
        )
        .join(
            FeedbackAnalysis,
            FeedbackAnalysis.feedback_id == Feedback.id,
        )
        .where(*base_filters)
        .group_by(FeedbackSource.source_type)
        .order_by(func.count(Feedback.id).desc())
    ).all()

    source_breakdown = [
        SourceAnalytics(
            source_type=_enum_value(source_type),
            count=count,
        )
        for source_type, count in source_rows
    ]

    # ---------------------------------------------------------
    # Feedback trend
    #
    # Prefer the timestamp from the original source.
    # Fall back to ingestion time when source timestamp
    # is unavailable.
    # ---------------------------------------------------------

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    feedback_timestamp = func.coalesce(
        Feedback.source_created_at,
        Feedback.ingested_at,
    )

    feedback_day = func.date(feedback_timestamp)

    trend_rows = db.execute(
        select(
            feedback_day.label("feedback_date"),
            func.count(Feedback.id),
        )
        .join(
            FeedbackAnalysis,
            FeedbackAnalysis.feedback_id == Feedback.id,
        )
        .where(*base_filters)
        .where(feedback_timestamp >= cutoff)
        .group_by(feedback_day)
        .order_by(feedback_day.asc())
    ).all()

    feedback_trend = [
        TrendValue(
            date=feedback_date,
            count=count,
        )
        for feedback_date, count in trend_rows
    ]

    # ---------------------------------------------------------
    # Most recent relevant feedback
    # ---------------------------------------------------------

    recent_rows = db.execute(
        select(
            Feedback.id,
            FeedbackSource.source_type,
            Feedback.raw_text,
            FeedbackAnalysis.sentiment,
            FeedbackAnalysis.category,
            FeedbackAnalysis.severity,
            Feedback.source_created_at,
        )
        .join(
            FeedbackSource,
            Feedback.source_id == FeedbackSource.id,
        )
        .join(
            FeedbackAnalysis,
            FeedbackAnalysis.feedback_id == Feedback.id,
        )
        .where(*base_filters)
        .order_by(
            func.coalesce(
                Feedback.source_created_at,
                Feedback.ingested_at,
            ).desc()
        )
        .limit(recent_limit)
    ).all()

    recent_feedback = [
        RecentFeedback(
            feedback_id=feedback_id,
            source_type=_enum_value(source_type),
            raw_text=raw_text,
            sentiment=_enum_value(sentiment),
            category=category,
            severity=_enum_value(severity),
            source_created_at=source_created_at,
        )
        for (
            feedback_id,
            source_type,
            raw_text,
            sentiment,
            category,
            severity,
            source_created_at,
        ) in recent_rows
    ]

    return ProjectAnalytics(
        project_id=project_id,
        relevant_feedback=relevant_feedback,
        sentiment_distribution=sentiment_distribution,
        category_distribution=category_distribution,
        source_breakdown=source_breakdown,
        feedback_trend=feedback_trend,
        recent_feedback=recent_feedback,
    )