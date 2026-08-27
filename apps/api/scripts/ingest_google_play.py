from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.feedback_source import FeedbackSource, SourceStatus, SourceType
from app.services.google_play_ingestion import ingest_google_play_reviews


db = SessionLocal()

try:
    # Find or create the Blinkit project
    project = db.execute(
        select(Project).where(Project.name == "Blinkit")
    ).scalar_one_or_none()

    if project is None:
        project = Project(
            name="Blinkit",
            description="Real-world validation project for the AI Product Discovery Engine",
        )
        db.add(project)
        db.flush()

    # Find or create the Google Play source
    source = db.execute(
        select(FeedbackSource).where(
            FeedbackSource.project_id == project.id,
            FeedbackSource.source_type == SourceType.GOOGLE_PLAY,
            FeedbackSource.external_reference == "com.grofers.customerapp",
        )
    ).scalar_one_or_none()

    if source is None:
        source = FeedbackSource(
            project_id=project.id,
            name="Blinkit Google Play",
            source_type=SourceType.GOOGLE_PLAY,
            external_reference="com.grofers.customerapp",
            configuration={
                "country": "in",
                "language": "en",
            },
            status=SourceStatus.ACTIVE,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

    print("Project ID:", project.id)
    print("Source ID:", source.id)

    result = ingest_google_play_reviews(
        db,
        project_id=project.id,
        source_id=source.id,
        app_id="com.grofers.customerapp",
        count=5,
    )

    print("Ingestion result:", result)

finally:
    db.close()