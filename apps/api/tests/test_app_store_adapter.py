from datetime import datetime, timezone
from types import SimpleNamespace

from app.adapters.app_store import adapt_app_store_review


def test_app_store_adapter():
    review = SimpleNamespace(
        id="14474161262",
        body="very helpful",
        rating=5,
        title="best",
        author_name="shaursu",
        app_version="18.75.0",
        store="appstore",
        country="in",
        updated_at=datetime(
            2026,
            8,
            26,
            12,
            55,
            11,
            tzinfo=timezone.utc,
        ),
    )

    result = adapt_app_store_review(review)

    assert result.external_id == "14474161262"
    assert result.text == "very helpful"
    assert result.rating == 5
    assert result.source_created_at == review.updated_at

    assert result.metadata["title"] == "best"
    assert result.metadata["author_name"] == "shaursu"
    assert result.metadata["app_version"] == "18.75.0"
    assert result.metadata["store"] == "appstore"
    assert result.metadata["country"] == "in"