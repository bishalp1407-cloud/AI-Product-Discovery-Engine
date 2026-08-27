import uuid

from sqlalchemy.orm import Session

from app.models.feedback import Feedback, ProcessingStatus
from app.schemas.feedback import FeedbackIngest
from app.services.content_hash import generate_content_hash
from app.services.deduplication import feedback_exists
from app.services.text_normalization import normalize_text
from app.services.language_detection import detect_language
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback_source import FeedbackSource


def ingest_feedback(
    db: Session,
    *,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    payload: FeedbackIngest,
) -> Feedback | None:
    source = db.execute(
        select(FeedbackSource).where(
            FeedbackSource.id == source_id,
            FeedbackSource.project_id == project_id,
        )
    ).scalar_one_or_none()

    if source is None:
        raise ValueError(
            "Feedback source does not exist or does not belong to this project."
        )

    if feedback_exists(
        db=db,
        source_id=source_id,
        external_id=payload.external_id,
    ):
        return None

    normalized_text = normalize_text(payload.text)
    content_hash = generate_content_hash(normalized_text)

    language = detect_language(payload.text)

    feedback = Feedback(
        project_id=project_id,
        source_id=source_id,
        external_id=payload.external_id,
        raw_text=payload.text,
        normalized_text=normalized_text,
        rating=payload.rating,
        source_created_at=payload.source_created_at,
        metadata_=payload.metadata,
        content_hash=content_hash,
        processing_status=ProcessingStatus.PENDING,
        language=language,
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return feedback