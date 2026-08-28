import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.feedback import Feedback, ProcessingStatus
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
)
from app.models.feedback_source import FeedbackSource
from app.models.project import Project
from app.schemas.feedback_analysis import FeedbackAnalysisResult
from app.services.feedback_analysis_service import analyze_and_store_feedback


def _create_feedback(db_session, text: str) -> Feedback:
    project = Project(
        id=uuid.uuid4(),
        name="Test Project",
    )

    source = FeedbackSource(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Test Source",
        source_type="google_play",
        external_reference="test-source",
        configuration={},
        status="active",
    )

    feedback = Feedback(
        id=uuid.uuid4(),
        project_id=project.id,
        source_id=source.id,
        external_id=str(uuid.uuid4()),
        raw_text=text,
        normalized_text=text,
        rating=None,
        source_created_at=datetime.now(timezone.utc),
        metadata_={},
        content_hash=str(uuid.uuid4()),
        processing_status=ProcessingStatus.PENDING,
        language="en",
    )

    # Insert in dependency order so PostgreSQL
    # foreign keys are satisfied.
    db_session.add(project)
    db_session.flush()

    db_session.add(source)
    db_session.flush()

    db_session.add(feedback)
    db_session.commit()

    return feedback


def test_low_quality_feedback_is_filtered_without_llm(
    db_session,
    monkeypatch,
):
    feedback = _create_feedback(
        db_session,
        "nice",
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError(
            "OpenRouter should not be called "
            "for low-quality feedback"
        )

    monkeypatch.setattr(
        "app.services.feedback_analysis_service."
        "analyze_feedback_with_openrouter",
        fail_if_called,
    )

    analysis = analyze_and_store_feedback(
        db_session,
        feedback=feedback,
    )

    assert analysis.analysis_status == AnalysisStatus.COMPLETED
    assert analysis.is_relevant is False
    assert analysis.category == "filtered_out"
    assert analysis.model_provider == "deterministic_filter"
    assert analysis.quality_score == 0.2


def test_good_feedback_is_analyzed_and_saved(
    db_session,
    monkeypatch,
):
    feedback = _create_feedback(
        db_session,
        "My order arrived very late and the food was cold.",
    )

    fake_result = FeedbackAnalysisResult(
        is_relevant=True,
        sentiment="negative",
        category="delivery",
        pain_point="late delivery caused cold food",
        severity="high",
        summary="The order arrived late and the food was cold.",
    )

    # Accept *args and **kwargs because the production
    # function now also receives source_type.
    monkeypatch.setattr(
        "app.services.feedback_analysis_service."
        "analyze_feedback_with_openrouter",
        lambda *args, **kwargs: fake_result,
    )

    analysis = analyze_and_store_feedback(
        db_session,
        feedback=feedback,
    )

    assert analysis.analysis_status == AnalysisStatus.COMPLETED
    assert analysis.is_relevant is True
    assert analysis.sentiment.value == "negative"
    assert analysis.category == "delivery"
    assert analysis.pain_point == (
        "late delivery caused cold food"
    )
    assert analysis.severity.value == "high"
    assert analysis.summary == (
        "The order arrived late and the food was cold."
    )
    assert analysis.model_provider == "openrouter"
    assert analysis.error_message is None


def test_llm_failure_is_saved_as_failed(
    db_session,
    monkeypatch,
):
    feedback = _create_feedback(
        db_session,
        "The payment failed but money was deducted.",
    )

    def raise_error(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "app.services.feedback_analysis_service."
        "analyze_feedback_with_openrouter",
        raise_error,
    )

    with pytest.raises(
        RuntimeError,
        match="provider unavailable",
    ):
        analyze_and_store_feedback(
            db_session,
            feedback=feedback,
        )

    analysis = db_session.execute(
        select(FeedbackAnalysis).where(
            FeedbackAnalysis.feedback_id == feedback.id
        )
    ).scalar_one()

    assert analysis.analysis_status == AnalysisStatus.FAILED
    assert "provider unavailable" in analysis.error_message


def test_raw_text_is_used_when_normalized_text_is_missing(
    db_session,
    monkeypatch,
):
    feedback = _create_feedback(
        db_session,
        "Delivery was very late and my order arrived cold.",
    )

    # Reproduce the real production-data condition
    # we discovered.
    feedback.normalized_text = None
    db_session.commit()

    captured_text = {}

    fake_result = FeedbackAnalysisResult(
        is_relevant=True,
        sentiment="negative",
        category="delivery",
        pain_point="late delivery caused cold food",
        severity="high",
        summary="The order arrived late and cold.",
    )

    # **kwargs allows source_type to be passed by
    # analyze_and_store_feedback.
    def fake_openrouter(text, **kwargs):
        captured_text["value"] = text
        return fake_result

    monkeypatch.setattr(
        "app.services.feedback_analysis_service."
        "analyze_feedback_with_openrouter",
        fake_openrouter,
    )

    analysis = analyze_and_store_feedback(
        db_session,
        feedback=feedback,
    )

    assert captured_text["value"] == (
        "Delivery was very late and my order arrived cold."
    )

    assert analysis.analysis_status == AnalysisStatus.COMPLETED
    assert analysis.is_relevant is True
    assert analysis.category == "delivery"
    assert analysis.model_provider == "openrouter"

def test_analysis_schema_rejects_unknown_category():
    with pytest.raises(ValueError):
        FeedbackAnalysisResult(
            is_relevant=True,
            sentiment="negative",
            category="Delivery Experience",
            pain_point="The delivery was late.",
            severity="medium",
            summary="The customer experienced a late delivery.",
        )