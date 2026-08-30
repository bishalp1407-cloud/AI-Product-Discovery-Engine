from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.insight_api import (
    InsightDetailResponse,
    InsightEvidenceItem,
    InsightListItem,
    InsightListResponse,
    InsightSourceBreakdown,
)
from app.schemas.project_overview import ProjectOverviewResponse
from app.services.insight_api_service import get_ranked_insights
from app.services.insight_detail_service import get_insight_detail
from app.services.project_overview_service import get_project_overview
from app.schemas.project_sync import (
    ProjectSyncResponse,
    SourceSyncResponse,
)
from app.services.project_sync_service import sync_project
from app.schemas.project_analytics import (
    DistributionItem,
    FeedbackTrendItem,
    ProjectAnalyticsResponse,
    RecentFeedbackItem,
    SourceAnalyticsItem,
)
from app.services.project_analytics_service import get_project_analytics



router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.get(
    "/{project_id}/overview",
    response_model=ProjectOverviewResponse,
)
def read_project_overview(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> ProjectOverviewResponse:
    overview = get_project_overview(
        db,
        project_id=project_id,
    )

    if overview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return ProjectOverviewResponse(
        project_id=overview.project_id,
        project_name=overview.project_name,
        total_feedback=overview.total_feedback,
        relevant_feedback=overview.relevant_feedback,
        source_count=overview.source_count,
        insight_count=overview.insight_count,
    )


@router.get(
    "/{project_id}/insights",
    response_model=InsightListResponse,
)
def read_ranked_insights(
    project_id: UUID,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> InsightListResponse:
    page = get_ranked_insights(
        db,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )

    return InsightListResponse(
        project_id=page.project_id,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        items=[
            InsightListItem(
                id=item.id,
                rank=item.rank,
                title=item.title,
                category=item.category,
                description=item.description,
                feedback_count=item.feedback_count,
                reach=item.reach,
                impact=item.impact,
                confidence=item.confidence,
                opportunity_score=item.opportunity_score,
            )
            for item in page.items
        ],
    )


@router.get(
    "/{project_id}/insights/{insight_id}",
    response_model=InsightDetailResponse,
)
def read_insight_detail(
    project_id: UUID,
    insight_id: UUID,
    db: Session = Depends(get_db),
) -> InsightDetailResponse:
    detail = get_insight_detail(
        db,
        project_id=project_id,
        insight_id=insight_id,
    )

    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    return InsightDetailResponse(
        id=detail.id,
        project_id=detail.project_id,
        title=detail.title,
        category=detail.category,
        description=detail.description,
        feedback_count=detail.feedback_count,
        reach=detail.reach,
        impact=detail.impact,
        confidence=detail.confidence,
        opportunity_score=detail.opportunity_score,
        source_breakdown=[
            InsightSourceBreakdown(
                source_type=item.source_type,
                evidence_count=item.evidence_count,
            )
            for item in detail.source_breakdown
        ],
        evidence=[
            InsightEvidenceItem(
                feedback_id=item.feedback_id,
                source_type=item.source_type,
                raw_text=item.raw_text,
                severity=item.severity,
                sentiment=item.sentiment,
            )
            for item in detail.evidence
        ],
    )

@router.post(
    "/{project_id}/sync",
    response_model=ProjectSyncResponse,
)
def sync_project_feedback(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> ProjectSyncResponse:
    result = sync_project(
        db,
        project_id=project_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return ProjectSyncResponse(
        project_id=result.project_id,
        sources_synced=result.sources_synced,
        feedback_fetched=result.feedback_fetched,
        feedback_created=result.feedback_created,
        duplicates=result.duplicates,
        analyses_completed=result.analyses_completed,
        analyses_failed=result.analyses_failed,
        insights_created=result.insights_created,
        sources=[
            SourceSyncResponse(
                source_id=source.source_id,
                source_name=source.source_name,
                source_type=source.source_type,
                fetched=source.fetched,
                created=source.created,
                duplicates=source.duplicates,
                error=source.error,
            )
            for source in result.sources
        ],
    )
@router.get(
    "/{project_id}/analytics",
    response_model=ProjectAnalyticsResponse,
)
def read_project_analytics(
    project_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    recent_limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ProjectAnalyticsResponse:
    analytics = get_project_analytics(
        db,
        project_id=project_id,
        days=days,
        recent_limit=recent_limit,
    )

    if analytics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return ProjectAnalyticsResponse(
        project_id=analytics.project_id,
        relevant_feedback=analytics.relevant_feedback,
        sentiment_distribution=[
            DistributionItem(
                name=item.name,
                count=item.count,
            )
            for item in analytics.sentiment_distribution
        ],
        category_distribution=[
            DistributionItem(
                name=item.name,
                count=item.count,
            )
            for item in analytics.category_distribution
        ],
        source_breakdown=[
            SourceAnalyticsItem(
                source_type=item.source_type,
                count=item.count,
            )
            for item in analytics.source_breakdown
        ],
        feedback_trend=[
            FeedbackTrendItem(
                date=item.date,
                count=item.count,
            )
            for item in analytics.feedback_trend
        ],
        recent_feedback=[
            RecentFeedbackItem(
                feedback_id=item.feedback_id,
                source_type=item.source_type,
                raw_text=item.raw_text,
                sentiment=item.sentiment,
                category=item.category,
                severity=item.severity,
                source_created_at=item.source_created_at,
            )
            for item in analytics.recent_feedback
        ],
    )