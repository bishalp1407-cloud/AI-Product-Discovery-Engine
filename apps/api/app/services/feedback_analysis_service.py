from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.feedback import Feedback
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
    Sentiment,
    Severity,
)
from app.models.feedback_source import FeedbackSource
from app.services.feedback_quality import evaluate_feedback_quality
from app.services.openrouter_client import (
    analyze_feedback_with_openrouter,
)


PROMPT_VERSION = "v3"


def analyze_and_store_feedback(
    db: Session,
    *,
    feedback: Feedback,
) -> FeedbackAnalysis:
    """
    Analyze one feedback record and persist the result.

    Production behavior:
    - Reuses an existing v3 analysis when present.
    - Skips already-completed v3 analyses.
    - Applies deterministic quality filtering first.
    - Uses OpenRouter only when AI analysis is required.
    - Avoids committing an intermediate PENDING state.
    - Persists COMPLETED or FAILED as the final state.
    """

    settings = get_settings()

    # Capture primitive values early.
    #
    # This is important because after rollback/connection errors,
    # SQLAlchemy ORM objects can become expired and accessing their
    # attributes may trigger another database query.
    feedback_id: UUID = feedback.id
    feedback_source_id: UUID = feedback.source_id

    analysis_text = (
        feedback.normalized_text
        or feedback.raw_text
        or ""
    )

    # ---------------------------------------------------------
    # Check for an existing v3 analysis
    # ---------------------------------------------------------

    analysis = db.execute(
        select(FeedbackAnalysis).where(
            FeedbackAnalysis.feedback_id == feedback_id,
            FeedbackAnalysis.prompt_version == PROMPT_VERSION,
        )
    ).scalar_one_or_none()

    # Already successfully analyzed.
    if (
        analysis is not None
        and analysis.analysis_status
        == AnalysisStatus.COMPLETED
    ):
        return analysis

    # ---------------------------------------------------------
    # Feedback quality gate
    # ---------------------------------------------------------

    quality = evaluate_feedback_quality(
        analysis_text
    )

    # ---------------------------------------------------------
    # Create/reuse analysis record
    # ---------------------------------------------------------

    if analysis is None:
        analysis = FeedbackAnalysis(
            feedback_id=feedback_id,
            prompt_version=PROMPT_VERSION,
            analysis_status=AnalysisStatus.PENDING,
        )
        db.add(analysis)

    else:
        analysis.analysis_status = AnalysisStatus.PENDING
        analysis.error_message = None

    analysis.quality_score = quality.quality_score

    # Flush rather than commit the intermediate PENDING state.
    #
    # This allows SQLAlchemy to send the pending INSERT/UPDATE
    # without creating a separate committed transaction.
    #
    # Successful analyses therefore require only one final commit.
    db.flush()

    # ---------------------------------------------------------
    # Deterministic filtering
    # ---------------------------------------------------------

    if not quality.should_analyze:
        try:
            analysis.is_relevant = False
            analysis.sentiment = Sentiment.NEUTRAL
            analysis.category = "filtered_out"
            analysis.pain_point = quality.reason
            analysis.severity = Severity.LOW
            analysis.summary = quality.reason

            analysis.model_provider = "deterministic_filter"
            analysis.model_name = None
            analysis.analysis_status = AnalysisStatus.COMPLETED
            analysis.error_message = None
            analysis.analyzed_at = datetime.now(
                timezone.utc
            )

            db.commit()

            return analysis

        except Exception:
            db.rollback()
            raise

    # ---------------------------------------------------------
    # AI analysis
    # ---------------------------------------------------------

    try:
        source = db.get(
            FeedbackSource,
            feedback_source_id,
        )

        source_type = (
            source.source_type.value
            if source is not None
            else None
        )

        result = analyze_feedback_with_openrouter(
            analysis_text,
            source_type=source_type,
        )

        analysis.is_relevant = result.is_relevant
        analysis.sentiment = Sentiment(
            result.sentiment
        )
        analysis.category = result.category
        analysis.pain_point = result.pain_point
        analysis.severity = Severity(
            result.severity
        )
        analysis.summary = result.summary

        analysis.model_provider = "openrouter"
        analysis.model_name = (
            settings.openrouter_model
        )

        analysis.analysis_status = (
            AnalysisStatus.COMPLETED
        )
        analysis.error_message = None
        analysis.analyzed_at = datetime.now(
            timezone.utc
        )

        # One final write transaction for the normal
        # successful AI-analysis path.
        db.commit()

        return analysis

    except Exception as exc:
        # The current transaction may contain an
        # uncommitted PENDING analysis.
        #
        # It may also have been invalidated by a
        # database/network error.
        db.rollback()

        try:
            # After rollback, retrieve an existing
            # persisted v3 analysis if one exists.
            failed_analysis = db.execute(
                select(FeedbackAnalysis).where(
                    FeedbackAnalysis.feedback_id
                    == feedback_id,
                    FeedbackAnalysis.prompt_version
                    == PROMPT_VERSION,
                )
            ).scalar_one_or_none()

            # If this was a newly-created analysis,
            # rollback removed the flushed-but-uncommitted
            # row. Recreate it directly as FAILED.
            if failed_analysis is None:
                failed_analysis = FeedbackAnalysis(
                    feedback_id=feedback_id,
                    quality_score=quality.quality_score,
                    prompt_version=PROMPT_VERSION,
                    analysis_status=AnalysisStatus.FAILED,
                )

                db.add(failed_analysis)

            failed_analysis.analysis_status = (
                AnalysisStatus.FAILED
            )

            failed_analysis.error_message = str(
                exc
            )

            failed_analysis.analyzed_at = (
                datetime.now(timezone.utc)
            )

            db.commit()

        except Exception:
            # Persisting FAILED is best-effort.
            #
            # For example, the original failure may
            # have occurred because Neon itself became
            # temporarily unreachable.
            db.rollback()

        # Preserve the original exception so the batch
        # runner can apply its retry policy.
        raise