from app_reviews import AppStoreReviews


def collect_app_store_reviews(
    app_id: str,
    *,
    country: str = "in",
    max_reviews: int = 20,
):
    client = AppStoreReviews()

    page = client.fetch_page(
        app_id,
        country=country,
    )

    return page.reviews[:max_reviews]