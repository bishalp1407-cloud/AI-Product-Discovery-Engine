import json

import httpx

from app.services.openrouter_client import (
    analyze_feedback_with_openrouter,
)


def test_openrouter_retries_temporary_failure(
    monkeypatch,
):
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
                            "pain_point": (
                                "late delivery"
                            ),
                            "severity": "medium",
                            "summary": (
                                "The customer's "
                                "delivery was late."
                            ),
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
            (
                "https://openrouter.ai/api/v1/"
                "chat/completions"
            ),
        )

        if attempts["count"] < 3:
            return httpx.Response(
                status_code=502,
                request=request,
                json={
                    "error": {
                        "message": (
                            "Provider temporarily "
                            "overloaded"
                        )
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

    # Avoid waiting during unit tests.
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


def test_openrouter_stops_after_max_retries(
    monkeypatch,
):
    attempts = {"count": 0}

    def always_fail(self, *args, **kwargs):
        attempts["count"] += 1

        request = httpx.Request(
            "POST",
            (
                "https://openrouter.ai/api/v1/"
                "chat/completions"
            ),
        )

        return httpx.Response(
            status_code=502,
            request=request,
            json={
                "error": {
                    "message": (
                        "Provider temporarily overloaded"
                    )
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
            "Expected HTTPStatusError after "
            "maximum retries"
        )

    assert attempts["count"] == 5


def test_retries_embedded_provider_error(
    monkeypatch,
):
    request = httpx.Request(
        "POST",
        (
            "https://openrouter.ai/api/v1/"
            "chat/completions"
        ),
    )

    responses = [
        httpx.Response(
            status_code=200,
            request=request,
            json={
                "error": {
                    "message": (
                        "Service temporarily overloaded"
                    ),
                    "code": 502,
                }
            },
        ),
        httpx.Response(
            status_code=200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "is_relevant": True,
                                    "sentiment": (
                                        "negative"
                                    ),
                                    "category": (
                                        "delivery"
                                    ),
                                    "pain_point": (
                                        "Delivery was "
                                        "delayed."
                                    ),
                                    "severity": "medium",
                                    "summary": (
                                        "Customer "
                                        "experienced a "
                                        "delayed delivery."
                                    ),
                                }
                            )
                        }
                    }
                ]
            },
        ),
    ]

    call_count = {"value": 0}

    def fake_post(
        self,
        url,
        headers=None,
        json=None,
    ):
        response = responses[
            call_count["value"]
        ]

        call_count["value"] += 1

        return response

    monkeypatch.setattr(
        httpx.Client,
        "post",
        fake_post,
    )

    monkeypatch.setattr(
        "app.services.openrouter_client.time.sleep",
        lambda _: None,
    )

    result = analyze_feedback_with_openrouter(
        "My delivery was delayed.",
        source_type="google_play",
    )

    assert call_count["value"] == 2
    assert result.is_relevant is True
    assert result.category == "delivery"
    assert result.severity == "medium"

def test_repairs_unquoted_enum_value():
    from app.services.openrouter_client import (
        repair_common_json_issues,
    )

    malformed = (
        '{"is_relevant": true, '
        '"sentiment": positive, '
        '"category": "pricing_fees", '
        '"pain_point": "Prices are cheaper", '
        '"severity": low, '
        '"summary": "Customer finds prices affordable."}'
    )

    repaired = repair_common_json_issues(
        malformed
    )

    import json

    parsed = json.loads(repaired)

    assert parsed["is_relevant"] is True
    assert parsed["sentiment"] == "positive"
    assert parsed["severity"] == "low"
    assert parsed["category"] == "pricing_fees"