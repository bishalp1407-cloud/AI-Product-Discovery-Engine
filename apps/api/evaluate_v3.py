from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.feedback import Feedback
from app.models.feedback_source import FeedbackSource
from app.services.feedback_analysis_service import (
    analyze_and_store_feedback,
)


SAMPLES_PER_SOURCE = 10

SOURCE_TYPES = [
    "youtube",
    "app_store",
    "google_play",
]


def main():
    db = SessionLocal()

    total = 0
    successful = 0
    failed = 0
    relevant = 0
    irrelevant = 0
    filtered = 0

    try:
        for source_type in SOURCE_TYPES:
            print("\n" + "=" * 100)
            print(f"SOURCE: {source_type.upper()}")
            print("=" * 100)

            feedback_items = db.execute(
                select(Feedback)
                .join(
                    FeedbackSource,
                    Feedback.source_id == FeedbackSource.id,
                )
                .where(
                    FeedbackSource.source_type == source_type
                )
                .order_by(func.random())
                .limit(SAMPLES_PER_SOURCE)
            ).scalars().all()

            for index, feedback in enumerate(
                feedback_items,
                start=1,
            ):
                total += 1

                text = (
                    feedback.normalized_text
                    or feedback.raw_text
                    or ""
                )

                print("\n" + "-" * 100)
                print(
                    f"{source_type.upper()} "
                    f"{index}/{len(feedback_items)}"
                )
                print(f"Feedback ID: {feedback.id}")
                print(f"Text: {text}")

                try:
                    analysis = analyze_and_store_feedback(
                        db,
                        feedback=feedback,
                    )

                    if (
                        analysis.model_provider
                        == "deterministic_filter"
                    ):
                        filtered += 1

                    if analysis.is_relevant is True:
                        relevant += 1

                    elif analysis.is_relevant is False:
                        irrelevant += 1

                    successful += 1

                    sentiment = (
                        analysis.sentiment.value
                        if analysis.sentiment
                        else None
                    )

                    severity = (
                        analysis.severity.value
                        if analysis.severity
                        else None
                    )

                    print(
                        f"Relevant: {analysis.is_relevant}"
                    )
                    print(
                        f"Sentiment: {sentiment}"
                    )
                    print(
                        f"Category: {analysis.category}"
                    )
                    print(
                        f"Severity: {severity}"
                    )
                    print(
                        f"Pain point: {analysis.pain_point}"
                    )
                    print(
                        f"Summary: {analysis.summary}"
                    )
                    print(
                        f"Provider: {analysis.model_provider}"
                    )
                    print(
                        f"Model: {analysis.model_name}"
                    )
                    print(
                        f"Prompt version: "
                        f"{analysis.prompt_version}"
                    )

                except Exception as exc:
                    failed += 1

                    print(
                        f"FAILED: "
                        f"{type(exc).__name__}: {exc}"
                    )

        print("\n" + "=" * 100)
        print("V3 EVALUATION SUMMARY")
        print("=" * 100)

        print(f"Total sampled: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Filtered: {filtered}")
        print(f"Marked relevant: {relevant}")
        print(f"Marked irrelevant: {irrelevant}")

        if total:
            print(
                "Overall success rate: "
                f"{successful / total * 100:.1f}%"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()