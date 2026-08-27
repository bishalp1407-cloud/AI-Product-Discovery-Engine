import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.feedback import FeedbackIngest
from app.services.feedback_ingestion import ingest_feedback


router = APIRouter(
    prefix="/projects/{project_id}/sources/{source_id}/feedback",
    tags=["feedback"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_feedback(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    payload: FeedbackIngest,
    db: Session = Depends(get_db),
):
    try:
        feedback = ingest_feedback(
        db,
        project_id=project_id,
        source_id=source_id,
        payload=payload,
    )
    except ValueError as exc:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(exc),
    ) from exc

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already exists for this source.",
        )

    return {
        "id": str(feedback.id),
        "project_id": str(feedback.project_id),
        "source_id": str(feedback.source_id),
        "external_id": feedback.external_id,
        "raw_text": feedback.raw_text,
        "normalized_text": feedback.normalized_text,
        "language": feedback.language,
        "rating": feedback.rating,
        "processing_status": feedback.processing_status.value,
    }