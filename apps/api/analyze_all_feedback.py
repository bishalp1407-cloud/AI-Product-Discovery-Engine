import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.session import SessionLocal
from app.models.feedback import Feedback
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
)
from app.services.feedback_analysis_service import (
    PROMPT_VERSION,
    analyze_and_store_feedback,
)


MAX_DB_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def load_work_queue() -> tuple[
    list[UUID],
    set[UUID],
]:
    """
    Load the bootstrap work queue using a small number of
    database queries.

    Returns:
    - all feedback IDs in processing order
    - feedback IDs already completed for the current
      prompt version

    This avoids making one completion-check query for every
    feedback record.
    """

    with SessionLocal() as db:
        feedback_ids = list(
            db.execute(
                select(Feedback.id).order_by(
                    Feedback.created_at,
                    Feedback.id,
                )
            ).scalars().all()
        )

        completed_ids = set(
            db.execute(
                select(
                    FeedbackAnalysis.feedback_id
                ).where(
                    FeedbackAnalysis.prompt_version
                    == PROMPT_VERSION,
                    FeedbackAnalysis.analysis_status
                    == AnalysisStatus.COMPLETED,
                )
            ).scalars().all()
        )

    return feedback_ids, completed_ids


def process_feedback(
    feedback_id: UUID,
) -> dict:
    """
    Analyze one feedback record using a fresh database session.

    Returning primitive values prevents the caller from
    accessing expired SQLAlchemy ORM objects after the
    session has closed or a connection has failed.
    """

    with SessionLocal() as db:
        feedback = db.get(
            Feedback,
            feedback_id,
        )

        if feedback is None:
            raise ValueError(
                f"Feedback {feedback_id} "
                "no longer exists."
            )

        analysis = analyze_and_store_feedback(
            db,
            feedback=feedback,
        )

        return {
            "status": analysis.analysis_status,
            "is_relevant": analysis.is_relevant,
            "category": analysis.category,
        }


def main() -> None:
    processed = 0
    completed = 0
    failed = 0

    # -----------------------------------------------------
    # Load the work queue once.
    # -----------------------------------------------------

    print("Loading feedback work queue...")

    feedback_ids, completed_ids = (
        load_work_queue()
    )

    total = len(feedback_ids)

    remaining_ids = [
        feedback_id
        for feedback_id in feedback_ids
        if feedback_id not in completed_ids
    ]

    already_completed = (
        total - len(remaining_ids)
    )

    print(f"Feedback records: {total}")
    print(
        "Already completed v3: "
        f"{already_completed}"
    )
    print(
        "Remaining to process: "
        f"{len(remaining_ids)}"
    )
    print(
        f"Prompt version: {PROMPT_VERSION}"
    )
    print("=" * 70)

    # -----------------------------------------------------
    # Process only unfinished feedback.
    # -----------------------------------------------------

    for position, feedback_id in enumerate(
        remaining_ids,
        start=1,
    ):
        last_exception = None

        for attempt in range(
            1,
            MAX_DB_RETRIES + 1,
        ):
            try:
                result = process_feedback(
                    feedback_id
                )

                processed += 1

                if (
                    result["status"]
                    == AnalysisStatus.COMPLETED
                ):
                    completed += 1

                    print(
                        f"[{position}/"
                        f"{len(remaining_ids)}] "
                        f"OK {feedback_id} "
                        f"| relevant="
                        f"{result['is_relevant']} "
                        f"| category="
                        f"{result['category']}"
                    )

                last_exception = None
                break

            except (
                OperationalError,
                DBAPIError,
            ) as exc:
                last_exception = exc

                print(
                    f"[{position}/"
                    f"{len(remaining_ids)}] "
                    f"DB RETRY "
                    f"{attempt}/"
                    f"{MAX_DB_RETRIES} "
                    f"{feedback_id} "
                    f"| {type(exc).__name__}"
                )

                if attempt < MAX_DB_RETRIES:
                    wait_seconds = (
                        RETRY_DELAY_SECONDS
                        * attempt
                    )

                    print(
                        "Waiting "
                        f"{wait_seconds}s "
                        "before retry..."
                    )

                    time.sleep(
                        wait_seconds
                    )

            except Exception as exc:
                # Provider errors, validation errors,
                # parsing failures, etc. are not blindly
                # retried by the bootstrap runner.
                #
                # Provider-specific retries already live
                # inside openrouter_client.py.
                last_exception = exc
                break

        if last_exception is not None:
            processed += 1
            failed += 1

            print(
                f"[{position}/"
                f"{len(remaining_ids)}] "
                f"FAILED {feedback_id} "
                f"| "
                f"{type(last_exception).__name__}: "
                f"{last_exception}"
            )

    # -----------------------------------------------------
    # Final summary
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)

    print(
        f"Total feedback: {total}"
    )

    print(
        "Already completed before run: "
        f"{already_completed}"
    )

    print(
        f"Attempted this run: {processed}"
    )

    print(
        f"Completed this run: {completed}"
    )

    print(
        f"Failed this run: {failed}"
    )

    print(
        "Expected completed total: "
        f"{already_completed + completed}"
    )


if __name__ == "__main__":
    main()