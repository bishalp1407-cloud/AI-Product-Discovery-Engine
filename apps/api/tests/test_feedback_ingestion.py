import uuid

from app.models.feedback import ProcessingStatus
from app.models.feedback_source import FeedbackSource, SourceStatus, SourceType
from app.models.project import Project
from app.schemas.feedback import FeedbackIngest
from app.services.feedback_ingestion import ingest_feedback
from fastapi.testclient import TestClient

from app.main import app
from app.api.feedback import get_db

def test_ingest_feedback(db_session):
    project = Project(
        name="Blinkit Ingestion Test",
        description="Milestone 3 ingestion test",
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

    payload = FeedbackIngest(
        external_id="review-123",
        text="  Delivery was VERY late!!!   ",
        rating=1,
        metadata={"app_version": "8.5.0"},
    )

    feedback = ingest_feedback(
        db_session,
        project_id=project.id,
        source_id=source.id,
        payload=payload,
    )

    assert feedback is not None
    assert feedback.raw_text == "  Delivery was VERY late!!!   "
    assert feedback.normalized_text == "delivery was very late!!!"
    assert feedback.rating == 1
    assert feedback.processing_status == ProcessingStatus.PENDING
    assert feedback.content_hash is not None
    assert feedback.language == "en"

    def test_duplicate_feedback_is_not_ingested(db_session):
        project = Project(
        name="Blinkit Dedup Test",
        description="Milestone 3 deduplication test",
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

    payload = FeedbackIngest(
        external_id="duplicate-review-123",
        text="Delivery was very late.",
        rating=1,
    )

    first_feedback = ingest_feedback(
        db_session,
        project_id=project.id,
        source_id=source.id,
        payload=payload,
    )

    second_feedback = ingest_feedback(
        db_session,
        project_id=project.id,
        source_id=source.id,
        payload=payload,
    )

    assert first_feedback is not None
    assert second_feedback is None

def test_feedback_ingestion_api(db_session):
    project = Project(
        name="Blinkit API Test",
        description="Milestone 3 API ingestion test",
    )
    db_session.add(project)
    db_session.flush()

    source = FeedbackSource(
        project_id=project.id,
        name="Blinkit Google Play API",
        source_type=SourceType.GOOGLE_PLAY,
        external_reference="com.grofers.customerapp",
        configuration={},
        status=SourceStatus.ACTIVE,
    )
    db_session.add(source)
    db_session.flush()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)

        response = client.post(
            f"/projects/{project.id}/sources/{source.id}/feedback",
            json={
                "external_id": "api-review-123",
                "text": "  Delivery was VERY late!!!   ",
                "rating": 1,
                "metadata": {
                    "app_version": "8.5.0"
                },
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["external_id"] == "api-review-123"
        assert data["raw_text"] == "  Delivery was VERY late!!!   "
        assert data["normalized_text"] == "delivery was very late!!!"
        assert data["language"] == "en"
        assert data["rating"] == 1
        assert data["processing_status"] == "pending"

        duplicate_response = client.post(
            f"/projects/{project.id}/sources/{source.id}/feedback",
            json={
                "external_id": "api-review-123",
                "text": "  Delivery was VERY late!!!   ",
                "rating": 1,
                "metadata": {
                    "app_version": "8.5.0"
                },
            },
        )

        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == (
            "Feedback already exists for this source."
        )

    finally:
        app.dependency_overrides.clear()

def test_feedback_source_must_belong_to_project(db_session):
    project_a = Project(
        name="Project A",
        description="First project",
    )

    project_b = Project(
        name="Project B",
        description="Second project",
    )

    db_session.add_all([project_a, project_b])
    db_session.flush()

    source = FeedbackSource(
        project_id=project_a.id,
        name="Project A Google Play",
        source_type=SourceType.GOOGLE_PLAY,
        external_reference="com.example.projecta",
        configuration={},
        status=SourceStatus.ACTIVE,
    )

    db_session.add(source)
    db_session.flush()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)

        response = client.post(
            f"/projects/{project_b.id}/sources/{source.id}/feedback",
            json={
                "external_id": "wrong-project-test",
                "text": "Delivery was late.",
                "rating": 1,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Feedback source does not exist or does not belong to this project."
        )

    finally:
        app.dependency_overrides.clear()