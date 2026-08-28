from sqlalchemy import select

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


def main():
    db = SessionLocal()

    processed = 0
    completed = 0
    failed = 0
    skipped = 0

    try:
        feedback_items = db.execute(
            select(Feedback)
            .order_by(Feedback.created_at)
        ).scalars().all()

        total = len(feedback_items)

        print(f"Feedback records: {total}")
        print(f"Prompt version: {PROMPT_VERSION}")
        print("=" * 70)

        for index, feedback in enumerate(
            feedback_items,
            start=1,
        ):
            existing = db.execute(
                select(FeedbackAnalysis).where(
                    FeedbackAnalysis.feedback_id
                    == feedback.id,
                    FeedbackAnalysis.prompt_version
                    == PROMPT_VERSION,
                    FeedbackAnalysis.analysis_status
                    == AnalysisStatus.COMPLETED,
                )
            ).scalar_one_or_none()

            if existing is not None:
                skipped += 1

                print(
                    f"[{index}/{total}] "
                    f"SKIP {feedback.id}"
                )
                continue

            try:
                analysis = analyze_and_store_feedback(
                    db,
                    feedback=feedback,
                )

                processed += 1

                if (
                    analysis.analysis_status
                    == AnalysisStatus.COMPLETED
                ):
                    completed += 1

                    print(
                        f"[{index}/{total}] "
                        f"OK {feedback.id} "
                        f"| relevant="
                        f"{analysis.is_relevant} "
                        f"| category="
                        f"{analysis.category}"
                    )

            except Exception as exc:
                processed += 1
                failed += 1

                print(
                    f"[{index}/{total}] "
                    f"FAILED {feedback.id} "
                    f"| {type(exc).__name__}: "
                    f"{exc}"
                )

        print("\n" + "=" * 70)
        print("BATCH COMPLETE")
        print("=" * 70)
        print(f"Total feedback: {total}")
        print(f"Already completed/skipped: {skipped}")
        print(f"Processed this run: {processed}")
        print(f"Completed this run: {completed}")
        print(f"Failed this run: {failed}")

    finally:
        db.close()


if __name__ == "__main__":
    main()