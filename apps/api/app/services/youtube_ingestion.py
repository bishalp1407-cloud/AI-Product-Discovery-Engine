import uuid

from sqlalchemy.orm import Session

from app.adapters.youtube import adapt_youtube_comment
from app.collectors.youtube import collect_youtube_comments_paginated
from app.services.feedback_ingestion import ingest_feedback
from app.services.youtube_video_discovery import discover_youtube_videos


def ingest_youtube_feedback(
    db: Session,
    *,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    query: str,
    top_videos: int = 3,
    comments_per_video: int = 10,
) -> dict:
    videos = discover_youtube_videos(
        query,
        top_n=top_videos,
    )

    fetched = 0
    created = 0
    duplicates = 0

    video_results = []

    for video in videos:
        video_id = video["video_id"]

        comments = collect_youtube_comments_paginated(
            video_id,
            target_count=comments_per_video,
        )

        video_created = 0
        video_duplicates = 0

        try:
            for comment in comments:
                payload = adapt_youtube_comment(comment)

                feedback = ingest_feedback(
                    db,
                    project_id=project_id,
                    source_id=source_id,
                    payload=payload,
                    commit=False,
                )

                fetched += 1

                if feedback is None:
                    duplicates += 1
                    video_duplicates += 1
                else:
                    created += 1
                    video_created += 1

            # Commit once per video instead of once per comment.
            db.commit()

        except Exception:
            db.rollback()
            raise

        video_results.append(
            {
                "video_id": video_id,
                "title": video["title"],
                "comments_fetched": len(comments),
                "created": video_created,
                "duplicates": video_duplicates,
            }
        )

        print(
            f"YouTube progress: {fetched} comments fetched | "
            f"{created} created | "
            f"{duplicates} duplicates"
        )

    return {
        "videos_discovered": len(videos),
        "comments_fetched": fetched,
        "created": created,
        "duplicates": duplicates,
        "videos": video_results,
    }