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
def collect_youtube_comments_paginated(
    video_id: str,
    *,
    target_count: int = 100,
) -> list[dict[str, Any]]:
    settings = get_settings()

    youtube = build(
        "youtube",
        "v3",
        developerKey=settings.youtube_api_key,
    )

    comments: list[dict[str, Any]] = []
    page_token = None

    while len(comments) < target_count:
        remaining = target_count - len(comments)

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(100, remaining),
            textFormat="plainText",
            order="time",
            pageToken=page_token,
        )

        response = request.execute()

        items = response.get("items", [])

        if not items:
            break

        comments.extend(items)

        page_token = response.get("nextPageToken")

        if page_token is None:
            break

    return comments[:target_count]