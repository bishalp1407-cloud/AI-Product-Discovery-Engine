from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback


def feedback_exists(
    db: Session,
    source_id,
    external_id: str | None,
) -> bool:
    if external_id is None:
        return False

    statement = select(Feedback.id).where(
        Feedback.source_id == source_id,
        Feedback.external_id == external_id,
    )

    return db.execute(statement).scalar_one_or_none() is not None