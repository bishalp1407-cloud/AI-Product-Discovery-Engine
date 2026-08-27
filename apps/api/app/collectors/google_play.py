from typing import Any

from google_play_scraper import Sort, reviews


def collect_google_play_reviews(
    app_id: str,
    *,
    count: int = 20,
    country: str = "in",
    language: str = "en",
) -> list[dict[str, Any]]:
    result, _ = reviews(
        app_id,
        lang=language,
        country=country,
        sort=Sort.NEWEST,
        count=count,
    )

    return result

def collect_google_play_review_page(
    app_id: str,
    *,
    count: int = 100,
    country: str = "in",
    language: str = "en",
    continuation_token=None,
):
    result, next_token = reviews(
        app_id,
        lang=language,
        country=country,
        sort=Sort.NEWEST,
        count=count,
        continuation_token=continuation_token,
    )

    return result, next_token