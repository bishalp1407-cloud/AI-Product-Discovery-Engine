from datetime import datetime
from typing import Any

from app.schemas.feedback import FeedbackIngest


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    return value


def adapt_google_play_review(
    review: dict[str, Any],
) -> FeedbackIngest:
    return FeedbackIngest(
        external_id=review.get("reviewId"),
        text=review["content"],
        rating=review.get("score"),
        source_created_at=review.get("at"),
        metadata={
            "user_name": review.get("userName"),
            "thumbs_up_count": review.get("thumbsUpCount"),
            "review_created_version": review.get("reviewCreatedVersion"),
            "reply_content": review.get("replyContent"),
            "replied_at": serialize_value(review.get("repliedAt")),
        },
    )