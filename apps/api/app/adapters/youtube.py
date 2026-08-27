from typing import Any

from app.schemas.feedback import FeedbackIngest


def adapt_youtube_comment(
    comment_thread: dict[str, Any],
) -> FeedbackIngest:
    thread_snippet = comment_thread["snippet"]

    top_level_comment = thread_snippet["topLevelComment"]
    comment_snippet = top_level_comment["snippet"]

    author_channel = comment_snippet.get("authorChannelId") or {}

    return FeedbackIngest(
        external_id=top_level_comment.get("id"),
        text=comment_snippet["textOriginal"],
        rating=None,
        source_created_at=comment_snippet.get("publishedAt"),
        metadata={
            "video_id": thread_snippet.get("videoId"),
            "author_name": comment_snippet.get("authorDisplayName"),
            "author_channel_id": author_channel.get("value"),
            "like_count": comment_snippet.get("likeCount", 0),
            "updated_at": comment_snippet.get("updatedAt"),
            "reply_count": thread_snippet.get("totalReplyCount", 0),
            "is_public": thread_snippet.get("isPublic", True),
        },
    )