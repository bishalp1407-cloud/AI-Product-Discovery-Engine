import json

import httpx

from app.services.openrouter_client import analyze_feedback_with_openrouter


def test_openrouter_retries_temporary_failure(monkeypatch):
    attempts = {"count": 0}

    successful_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "is_relevant": True,
                            "sentiment": "negative",
                            "category": "delivery",
                            "pain_point": "late delivery",
                            "severity": "medium",
                            "summary": "The customer's delivery was late.",
                        }
                    )
                }
            }
        ]
    }

    def fake_post(self, *args, **kwargs):
        attempts["count"] += 1

        request = httpx.Request(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
        )

        if attempts["count"] < 3:
            return httpx.Response(
                status_code=502,
                request=request,
                json={
                    "error": {
                        "message": "Provider temporarily overloaded"
                    }
                },
            )

        return httpx.Response(
            status_code=200,
            request=request,
            json=successful_payload,
        )

    monkeypatch.setattr(
        httpx.Client,
        "post",
        fake_post,
    )

    # Avoid actually waiting 2s + 4s during the unit test.
    monkeypatch.setattr(
        "app.services.openrouter_client.time.sleep",
        lambda _: None,
    )

    result = analyze_feedback_with_openrouter(
        "My delivery was late."
    )

    assert attempts["count"] == 3
    assert result.is_relevant is True
    assert result.sentiment == "negative"
    assert result.category == "delivery"

def test_openrouter_stops_after_max_retries(monkeypatch):
    attempts = {"count": 0}

    def always_fail(self, *args, **kwargs):
        attempts["count"] += 1

        request = httpx.Request(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
        )

        return httpx.Response(
            status_code=502,
            request=request,
            json={
                "error": {
                    "message": "Provider temporarily overloaded"
                }
            },
        )

    monkeypatch.setattr(
        httpx.Client,
        "post",
        always_fail,
    )

    monkeypatch.setattr(
        "app.services.openrouter_client.time.sleep",
        lambda _: None,
    )

    try:
        analyze_feedback_with_openrouter(
            "My delivery was very late."
        )
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError(
            "Expected HTTPStatusError after maximum retries"
        )

    assert attempts["count"] == 5