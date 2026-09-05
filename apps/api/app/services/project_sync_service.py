from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
)
from app.models.feedback_source import (
    FeedbackSource,
    SourceStatus,
    SourceType,
)
from app.models.project import Project
from app.services.app_store_ingestion import (
    ingest_app_store_reviews_paginated,
)
from app.services.feedback_analysis_service import (
    PROMPT_VERSION,
    analyze_and_store_feedback,
)
from app.services.google_play_ingestion import (
    ingest_google_play_reviews_paginated,
)
from app.services.insight_engine_service import rebuild_project_insights
from app.services.youtube_ingestion import ingest_youtube_feedback
from app.services.sync_cancellation import SyncCancelledError


ProgressCallback = Callable[..., None]
CancellationCallback = Callable[[], bool]




@dataclass
class SourceSyncResult:
    source_id: UUID
    source_name: str
    source_type: str
    fetched: int = 0
    created: int = 0
    duplicates: int = 0
    error: str | None = None


@dataclass
class ProjectSyncResult:
    project_id: UUID
    sources_synced: int
    feedback_fetched: int
    feedback_created: int
    duplicates: int
    analyses_completed: int
    analyses_failed: int
    insights_created: int
    sources: list[SourceSyncResult] = field(
        default_factory=list
    )


def _report_progress(
    progress_callback: ProgressCallback | None,
    **kwargs,
) -> None:
    """
    Report sync progress when a callback is provided.
    """
    if progress_callback is not None:
        progress_callback(**kwargs)

def _check_cancellation(
    cancellation_callback: CancellationCallback | None,
) -> None:
    """
    Stop the sync when cancellation has been requested.
    """
    if (
        cancellation_callback is not None
        and cancellation_callback()
    ):
        raise SyncCancelledError("Sync cancelled by user.")

def _sync_source(
    db: Session,
    *,
    source: FeedbackSource,
) -> SourceSyncResult:
    config = source.configuration or {}

    if source.source_type == SourceType.GOOGLE_PLAY:
        if not source.external_reference:
            raise ValueError(
                "Google Play source is missing external_reference."
            )

        result = ingest_google_play_reviews_paginated(
            db,
            project_id=source.project_id,
            source_id=source.id,
            app_id=source.external_reference,
            target_count=int(
                config.get("target_count", 100)
            ),
            batch_size=int(
                config.get("batch_size", 100)
            ),
            country=str(
                config.get("country", "in")
            ),
            language=str(
                config.get("language", "en")
            ),
        )

        fetched = result["fetched"]

    elif source.source_type == SourceType.APP_STORE:
        if not source.external_reference:
            raise ValueError(
                "App Store source is missing external_reference."
            )

        result = ingest_app_store_reviews_paginated(
            db,
            project_id=source.project_id,
            source_id=source.id,
            app_id=source.external_reference,
            target_count=int(
                config.get("target_count", 100)
            ),
            country=str(
                config.get("country", "in")
            ),
        )

        fetched = result["fetched"]

    elif source.source_type == SourceType.YOUTUBE:
        query = config.get("query")

        if not query:
            query = source.external_reference

        if not query:
            raise ValueError(
                "YouTube source is missing a query."
            )

        result = ingest_youtube_feedback(
            db,
            project_id=source.project_id,
            source_id=source.id,
            query=str(query),
            top_videos=int(
                config.get("top_videos", 3)
            ),
            comments_per_video=int(
                config.get(
                    "comments_per_video",
                    10,
                )
            ),
        )

        fetched = result["comments_fetched"]

    else:
        raise ValueError(
            f"Sync is not implemented for source type "
            f"'{source.source_type.value}'."
        )

    source.last_synced_at = datetime.now(
        timezone.utc
    )

    db.commit()
    db.refresh(source)

    return SourceSyncResult(
        source_id=source.id,
        source_name=source.name,
        source_type=source.source_type.value,
        fetched=fetched,
        created=result["created"],
        duplicates=result["duplicates"],
    )


def _get_feedback_needing_analysis(
    db: Session,
    *,
    project_id: UUID,
) -> list[Feedback]:
    completed_current_analysis = exists().where(
        FeedbackAnalysis.feedback_id == Feedback.id,
        FeedbackAnalysis.prompt_version
        == PROMPT_VERSION,
        FeedbackAnalysis.analysis_status
        == AnalysisStatus.COMPLETED,
    )

    return list(
        db.execute(
            select(Feedback)
            .where(
                Feedback.project_id == project_id,
                ~completed_current_analysis,
            )
            .order_by(
                Feedback.created_at.asc()
            )
        )
        .scalars()
        .all()
    )


def sync_project(
    db: Session,
    *,
    project_id: UUID,
    progress_callback: ProgressCallback | None = None,
    cancellation_callback: CancellationCallback | None = None,
) -> ProjectSyncResult | None:

    sources = list(
        db.execute(
            select(FeedbackSource)
            .where(
                FeedbackSource.project_id == project_id,
                FeedbackSource.status
                == SourceStatus.ACTIVE,
            )
            .order_by(
                FeedbackSource.created_at.asc()
            )
        )
        .scalars()
        .all()
    )

    source_results: list[SourceSyncResult] = []

    total_fetched = 0
    total_created = 0
    total_duplicates = 0

    # =========================================================
    # STAGE 1 — INGESTING
    # =========================================================

    _report_progress(
        progress_callback,
        current_stage="ingesting",
        total_items=len(sources),
        processed_items=0,
        total_batches=0,
        completed_batches=0,
    )

    for index, source in enumerate(sources):
        _check_cancellation(cancellation_callback)
        try:
            result = _sync_source(
                db,
                source=source,
            )

        except Exception as exc:
            result = SourceSyncResult(
                source_id=source.id,
                source_name=source.name,
                source_type=source.source_type.value,
                error=str(exc),
            )

        source_results.append(result)

        total_fetched += result.fetched
        total_created += result.created
        total_duplicates += result.duplicates

        _report_progress(
            progress_callback,
            current_stage="ingesting",
            processed_items=index + 1,
        )

    # =========================================================
    # STAGE 2 — ANALYZING
    # =========================================================

    feedback_to_analyze = (
        _get_feedback_needing_analysis(
            db,
            project_id=project_id,
        )
    )

    analyses_completed = 0
    analyses_failed = 0

    _report_progress(
        progress_callback,
        current_stage="analyzing",
        total_items=len(feedback_to_analyze),
        processed_items=0,
        total_batches=0,
        completed_batches=0,
    )

    for index, feedback in enumerate(
        feedback_to_analyze
    ):
        _check_cancellation(cancellation_callback)
        try:
            analyze_and_store_feedback(
                db,
                feedback=feedback,
            )

            analyses_completed += 1

        except Exception:
            analyses_failed += 1

        _report_progress(
            progress_callback,
            current_stage="analyzing",
            processed_items=index + 1,
        )

    # =========================================================
    # STAGE 3 — GENERATING INSIGHTS
    # =========================================================

    _report_progress(
        progress_callback,
        current_stage="generating_insights",
        total_items=0,
        processed_items=0,
        total_batches=1,
        completed_batches=0,
    )
    _check_cancellation(cancellation_callback)

    insight_result = rebuild_project_insights(
        db,
        project_id=project_id,
    )

    _report_progress(
        progress_callback,
        current_stage="generating_insights",
        completed_batches=1,
    )

    return ProjectSyncResult(
        project_id=project_id,
        sources_synced=sum(
            1
            for result in source_results
            if result.error is None
        ),
        feedback_fetched=total_fetched,
        feedback_created=total_created,
        duplicates=total_duplicates,
        analyses_completed=analyses_completed,
        analyses_failed=analyses_failed,
        insights_created=(
            insight_result.persisted_insight_count
        ),
        sources=source_results,
    )