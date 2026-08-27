from app.adapters.youtube import adapt_youtube_comment


def test_youtube_adapter():
    comment = {
        "id": "UgwyfIYD3J9zjDVws914AaABAg",
        "snippet": {
            "videoId": "BYHwR4uVyWI",
            "topLevelComment": {
                "id": "UgwyfIYD3J9zjDVws914AaABAg",
                "snippet": {
                    "videoId": "BYHwR4uVyWI",
                    "textOriginal": "Blinkit delivery was very late",
                    "authorDisplayName": "@testuser",
                    "authorChannelId": {
                        "value": "test-channel-id"
                    },
                    "likeCount": 4,
                    "publishedAt": "2026-08-26T05:56:33Z",
                    "updatedAt": "2026-08-26T06:00:00Z",
                },
            },
            "totalReplyCount": 2,
            "isPublic": True,
        },
    }

    result = adapt_youtube_comment(comment)

    assert result.external_id == "UgwyfIYD3J9zjDVws914AaABAg"
    assert result.text == "Blinkit delivery was very late"

    # YouTube has no star-rating concept.
    assert result.rating is None

    assert result.metadata["video_id"] == "BYHwR4uVyWI"
    assert result.metadata["author_name"] == "@testuser"
    assert result.metadata["author_channel_id"] == "test-channel-id"
    assert result.metadata["like_count"] == 4
    assert result.metadata["reply_count"] == 2
    assert result.metadata["is_public"] is True