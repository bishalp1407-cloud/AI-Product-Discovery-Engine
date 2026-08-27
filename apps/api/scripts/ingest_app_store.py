from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.feedback_source import FeedbackSource, SourceStatus, SourceType
from app.services.app_store_ingestion import (
    ingest_app_store_reviews_paginated,
)


db = SessionLocal()

try:
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

    source = db.execute(
        select(FeedbackSource).where(
            FeedbackSource.project_id == project.id,
            FeedbackSource.source_type == SourceType.APP_STORE,
            FeedbackSource.external_reference == "960335206",
        )
    ).scalar_one_or_none()

    if source is None:
        source = FeedbackSource(
            project_id=project.id,
            name="Blinkit App Store",
            source_type=SourceType.APP_STORE,
            external_reference="960335206",
            configuration={
                "country": "in",
            },
            status=SourceStatus.ACTIVE,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

    print("Project ID:", project.id)
    print("Source ID:", source.id)

    result = ingest_app_store_reviews_paginated(
    db,
    project_id=project.id,
    source_id=source.id,
    app_id="960335206",
    target_count=300,
    country="in",
)

    print("Ingestion result:", result)

finally:
    db.close()


