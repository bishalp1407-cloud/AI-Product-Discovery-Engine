from datetime import datetime, timezone

from app.adapters.google_play import adapt_google_play_review
from app.models.feedback import ProcessingStatus
from app.models.feedback_source import FeedbackSource, SourceStatus, SourceType
from app.models.project import Project
from app.services.feedback_ingestion import ingest_feedback

def test_google_play_adapter():
    review = {
        "reviewId": "google-review-123",
        "userName": "Test User",
        "content": "Delivery was very late!",
        "score": 1,
        "thumbsUpCount": 7,
        "reviewCreatedVersion": "8.5.0",
        "at": datetime(
            2026,
            8,
            27,
            10,
            30,
            tzinfo=timezone.utc,
        ),
        "replyContent": None,
        "repliedAt": None,
    }

    result = adapt_google_play_review(review)

    assert result.external_id == "google-review-123"
    assert result.text == "Delivery was very late!"
    assert result.rating == 1
    assert result.source_created_at == review["at"]

    assert result.metadata["user_name"] == "Test User"
    assert result.metadata["thumbs_up_count"] == 7
    assert result.metadata["review_created_version"] == "8.5.0"

def test_google_play_adapter_to_database(db_session):
    project = Project(
        name="Blinkit Google Play Integration",
        description="Adapter to ingestion integration test",
    )
    db_session.add(project)
    db_session.flush()

    source = FeedbackSource(
        project_id=project.id,
        name="Blinkit Google Play",
        source_type=SourceType.GOOGLE_PLAY,
        external_reference="com.grofers.customerapp",
        configuration={},
        status=SourceStatus.ACTIVE,
    )
    db_session.add(source)
    db_session.flush()

    review = {
        "reviewId": "integration-review-123",
        "userName": "Test User",
        "content": "  Delivery was VERY late!!!   ",
        "score": 1,
        "thumbsUpCount": 12,
        "reviewCreatedVersion": "8.5.0",
        "at": datetime(
            2026,
            8,
            27,
            10,
            30,
            tzinfo=timezone.utc,
        ),
        "replyContent": None,
        "repliedAt": None,
    }

    payload = adapt_google_play_review(review)

    feedback = ingest_feedback(
        db_session,
        project_id=project.id,
        source_id=source.id,
        payload=payload,
    )

    assert feedback is not None

    assert feedback.external_id == "integration-review-123"
    assert feedback.raw_text == "  Delivery was VERY late!!!   "
    assert feedback.normalized_text == "delivery was very late!!!"
    assert feedback.rating == 1
    assert feedback.language == "en"

    assert feedback.metadata_["thumbs_up_count"] == 12
    assert feedback.metadata_["review_created_version"] == "8.5.0"

    assert feedback.content_hash is not None
    assert feedback.processing_status == ProcessingStatus.PENDING