from typing import Any

from googleapiclient.discovery import build

from app.core.config import get_settings


def collect_youtube_comments(
    video_id: str,
    *,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    settings = get_settings()

    youtube = build(
        "youtube",
        "v3",
        developerKey=settings.youtube_api_key,
    )

    response = (
        youtube.commentThreads()
        .list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            textFormat="plainText",
            order="time",
        )
        .execute()
    )

    return response.get("items", [])