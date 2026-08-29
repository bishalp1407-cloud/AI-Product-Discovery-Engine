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
from app.models.project import Project


@dataclass(frozen=True)
class ProjectOverview:
    project_id: UUID
    project_name: str
    total_feedback: int
    relevant_feedback: int
    source_count: int
    insight_count: int


def get_project_overview(
    db: Session,
    *,
    project_id: UUID,
) -> ProjectOverview | None:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
    )

    if project is None:
        return None

    total_feedback = db.scalar(
        select(func.count(Feedback.id))
        .where(Feedback.project_id == project_id)
    ) or 0

    relevant_feedback = db.scalar(
        select(func.count(FeedbackAnalysis.id))
        .join(
            Feedback,
            Feedback.id == FeedbackAnalysis.feedback_id,
        )
        .where(
            Feedback.project_id == project_id,
            FeedbackAnalysis.analysis_status
            == AnalysisStatus.COMPLETED,
            FeedbackAnalysis.is_relevant.is_(True),
            FeedbackAnalysis.prompt_version == "v3",
        )
    ) or 0

    source_count = db.scalar(
        select(func.count(FeedbackSource.id))
        .where(
            FeedbackSource.project_id == project_id
        )
    ) or 0

    insight_count = db.scalar(
        select(func.count(Insight.id))
        .where(Insight.project_id == project_id)
    ) or 0

    return ProjectOverview(
        project_id=project.id,
        project_name=project.name,
        total_feedback=total_feedback,
        relevant_feedback=relevant_feedback,
        source_count=source_count,
        insight_count=insight_count,
    )