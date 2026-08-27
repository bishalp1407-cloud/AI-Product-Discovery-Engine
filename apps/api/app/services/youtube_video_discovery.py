from typing import Any

from googleapiclient.discovery import build

from app.core.config import get_settings


def discover_youtube_videos(
    query: str,
    *,
    max_candidates: int = 10,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    settings = get_settings()

    youtube = build(
        "youtube",
        "v3",
        developerKey=settings.youtube_api_key,
    )

    # Step 1: discover relevant videos
    search_response = (
        youtube.search()
        .list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_candidates,
            order="relevance",
        )
        .execute()
    )

    video_ids = [
        item["id"]["videoId"]
        for item in search_response.get("items", [])
    ]

    if not video_ids:
        return []

    # Step 2: retrieve statistics for those videos
    videos_response = (
        youtube.videos()
        .list(
            part="snippet,statistics",
            id=",".join(video_ids),
        )
        .execute()
    )

    candidates = []

    for item in videos_response.get("items", []):
        statistics = item.get("statistics", {})
        snippet = item.get("snippet", {})

        candidates.append(
            {
                "video_id": item["id"],
                "title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "comment_count": int(statistics.get("commentCount", 0)),
            }
        )

    # MVP ranking: comments matter most because
    # our objective is customer-feedback discovery.
    candidates.sort(
        key=lambda video: (
            video["comment_count"],
            video["view_count"],
        ),
        reverse=True,
    )

    return candidates[:top_n]