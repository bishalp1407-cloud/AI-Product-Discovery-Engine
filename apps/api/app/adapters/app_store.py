from typing import Any

from app.schemas.feedback import FeedbackIngest


def adapt_app_store_review(review: Any) -> FeedbackIngest:
    return FeedbackIngest(
        external_id=str(review.id) if review.id is not None else None,
        text=review.body,
        rating=review.rating,
        source_created_at=review.updated_at,
        metadata={
            "title": review.title,
            "author_name": review.author_name,
            "app_version": review.app_version,
            "store": review.store,
            "country": review.country,
        },
    )