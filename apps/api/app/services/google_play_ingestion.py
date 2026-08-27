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

def ingest_google_play_reviews_paginated(
    db: Session,
    *,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    app_id: str,
    target_count: int = 500,
    batch_size: int = 100,
    country: str = "in",
    language: str = "en",
) -> dict[str, int]:
    from app.collectors.google_play import collect_google_play_review_page

    fetched = 0
    created = 0
    duplicates = 0
    continuation_token = None

    while fetched < target_count:
        remaining = target_count - fetched
        current_batch_size = min(batch_size, remaining)

        reviews, continuation_token = collect_google_play_review_page(
            app_id,
            count=current_batch_size,
            country=country,
            language=language,
            continuation_token=continuation_token,
        )

        if not reviews:
            break

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

        fetched += len(reviews)

        print(
            f"Progress: {fetched}/{target_count} fetched | "
            f"{created} created | "
            f"{duplicates} duplicates"
        )

        if continuation_token is None:
            break

    return {
        "fetched": fetched,
        "created": created,
        "duplicates": duplicates,
    }