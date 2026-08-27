import uuid

from sqlalchemy.orm import Session

from app.adapters.app_store import adapt_app_store_review
from app.collectors.app_store import (
    collect_app_store_review_page,
    collect_app_store_reviews,
)
from app.services.feedback_ingestion import ingest_feedback


def ingest_app_store_reviews(
    db: Session,
    *,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    app_id: str,
    count: int = 20,
) -> dict[str, int]:
    reviews = collect_app_store_reviews(
        app_id,
        max_reviews=count,
    )

    created = 0
    duplicates = 0

    for review in reviews:
        payload = adapt_app_store_review(review)

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


def ingest_app_store_reviews_paginated(
    db: Session,
    *,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    app_id: str,
    target_count: int = 300,
    country: str = "in",
) -> dict[str, int]:
    fetched = 0
    created = 0
    duplicates = 0
    cursor: str | None = None

    while fetched < target_count:
        page = collect_app_store_review_page(
            app_id,
            country=country,
            cursor=cursor,
        )

        if page.error is not None:
            print(f"App Store collector error: {page.error}")
            break

        reviews = page.reviews

        if not reviews:
            break

        # Prevent the final page from exceeding target_count.
        remaining = target_count - fetched
        reviews = reviews[:remaining]

        for review in reviews:
            payload = adapt_app_store_review(review)

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

        if page.next_cursor is None:
            break

        cursor = str(page.next_cursor)

    return {
        "fetched": fetched,
        "created": created,
        "duplicates": duplicates,
    }