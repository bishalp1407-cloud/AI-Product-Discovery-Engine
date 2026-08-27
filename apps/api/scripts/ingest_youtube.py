from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.feedback_source import FeedbackSource, SourceStatus, SourceType
from app.models.project import Project
from app.services.youtube_ingestion import ingest_youtube_feedback


db = SessionLocal()

try:
    project = db.execute(
        select(Project).where(Project.name == "Blinkit")
    ).scalar_one()

    source = db.execute(
        select(FeedbackSource).where(
            FeedbackSource.project_id == project.id,
            FeedbackSource.source_type == SourceType.YOUTUBE,
        )
    ).scalar_one_or_none()

    if source is None:
        source = FeedbackSource(
            project_id=project.id,
            name="Blinkit YouTube",
            source_type=SourceType.YOUTUBE,
            external_reference="blinkit",
            configuration={
                "query": "Blinkit India",
                "top_videos": 2,
                "comments_per_video": 3,
            },
            status=SourceStatus.ACTIVE,
        )

        db.add(source)
        db.commit()
        db.refresh(source)

    print("Project ID:", project.id)
    print("Source ID:", source.id)

    result = ingest_youtube_feedback(
    db,
    project_id=project.id,
    source_id=source.id,
    query="Blinkit India",
    top_videos=5,
    comments_per_video=60,
)

    print("YouTube ingestion result:")
    print(result)

finally:
    db.close()