from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.feedback import Feedback
from app.models.feedback_source import FeedbackSource
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
    Sentiment,
    Severity,
)
from app.services.feedback_quality import evaluate_feedback_quality
from app.services.openrouter_client import analyze_feedback_with_openrouter


PROMPT_VERSION = "v3"


def analyze_and_store_feedback(
    db: Session,
    *,
    feedback: Feedback,
) -> FeedbackAnalysis:
    settings = get_settings()

    # Avoid analyzing the same feedback twice
    # for the same prompt version.
    existing = db.execute(
        select(FeedbackAnalysis).where(
            FeedbackAnalysis.feedback_id == feedback.id,
            FeedbackAnalysis.prompt_version == PROMPT_VERSION,
        )
    ).scalar_one_or_none()

    # If this feedback was already successfully analyzed
    # with the current prompt version, reuse the result.
    if (
        existing is not None
        and existing.analysis_status == AnalysisStatus.COMPLETED
    ):
        return existing

    # Prefer normalized text, but fall back to raw text.
    # Some historical feedback records may not have
    # normalized_text populated.
    analysis_text = (
        feedback.normalized_text
        or feedback.raw_text
        or ""
    )

    # Run the cheap deterministic quality filter first.
    quality = evaluate_feedback_quality(
        analysis_text
    )

    # Reuse a failed/pending analysis record if one exists.
    # Otherwise create a new analysis record.
    if existing is not None:
        analysis = existing
        analysis.analysis_status = AnalysisStatus.PENDING
        analysis.error_message = None

    else:
        analysis = FeedbackAnalysis(
            feedback_id=feedback.id,
            quality_score=quality.quality_score,
            prompt_version=PROMPT_VERSION,
            analysis_status=AnalysisStatus.PENDING,
        )

        db.add(analysis)

    analysis.quality_score = quality.quality_score

    db.commit()
    db.refresh(analysis)

    # ---------------------------------------------------------
    # Deterministic quality filtering
    # ---------------------------------------------------------
    #
    # Obvious low-information feedback such as:
    #
    # "good"
    # "nice"
    # emoji-only comments
    #
    # does not need an LLM call.
    #
    if not quality.should_analyze:
        analysis.is_relevant = False
        analysis.category = "filtered_out"
        analysis.pain_point = quality.reason

        analysis.summary = (
            "Feedback excluded by deterministic "
            f"quality filter: {quality.reason}."
        )

        analysis.model_provider = "deterministic_filter"
        analysis.model_name = None

        analysis.analysis_status = AnalysisStatus.COMPLETED
        analysis.analyzed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(analysis)

        return analysis

    # ---------------------------------------------------------
    # AI analysis
    # ---------------------------------------------------------

    try:
        # Feedback only stores source_id.
        # Fetch the corresponding FeedbackSource so that
        # we can give the model useful source context.
        source = db.get(
            FeedbackSource,
            feedback.source_id,
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

        # Store the validated structured model output.
        analysis.is_relevant = result.is_relevant
        analysis.sentiment = Sentiment(result.sentiment)
        analysis.category = result.category
        analysis.pain_point = result.pain_point
        analysis.severity = Severity(result.severity)
        analysis.summary = result.summary

        analysis.model_provider = "openrouter"
        analysis.model_name = settings.openrouter_model

        analysis.analysis_status = AnalysisStatus.COMPLETED
        analysis.error_message = None
        analysis.analyzed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(analysis)

        return analysis

    except Exception as exc:
        # Persist the failure so that:
        #
        # 1. failures are observable,
        # 2. they can be retried later,
        # 3. we don't silently lose analysis attempts.
        analysis.analysis_status = AnalysisStatus.FAILED
        analysis.error_message = str(exc)
        analysis.analyzed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(analysis)

        raise