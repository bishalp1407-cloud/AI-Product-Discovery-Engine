import uuid

from sqlalchemy.orm import Session

from app.adapters.google_play import adapt_google_play_review
from app.collectors.google_play import collect_google_play_reviews
from app.services.feedback_ingestion import ingest_feedback


def ingest_google_play_reviews(
    db: Session,
    *,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    app_id: str,
    count: int = 20,
) -> dict[str, int]:
    reviews = collect_google_play_reviews(
        app_id,
        count=count,
    )

    created = 0
    duplicates = 0

    for review in reviews:
        payload = adapt_google_play_review(review)

        feedback = ingest_feedback(
            db,
            project_id=project_id,
            source_id=source_id,
            payload=payload,
        )

        if feedback is None:
            duplicates += 1
        else:
            created += 1

    return {
        "fetched": len(reviews),
        "created": created,
        "duplicates": duplicates,
    }