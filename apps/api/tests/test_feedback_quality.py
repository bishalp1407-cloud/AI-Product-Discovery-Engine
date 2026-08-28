from app.services.feedback_quality import evaluate_feedback_quality


def test_empty_feedback_is_rejected():
    result = evaluate_feedback_quality("")

    assert result.should_analyze is False
    assert result.quality_score == 0.0
    assert result.reason == "empty_text"


def test_emoji_only_feedback_is_rejected():
    result = evaluate_feedback_quality("😂😂😂")

    assert result.should_analyze is False
    assert result.reason == "no_meaningful_text"


def test_very_short_feedback_is_rejected():
    result = evaluate_feedback_quality("nice")

    assert result.should_analyze is False
    assert result.quality_score == 0.2
    assert result.reason == "too_short"


def test_short_meaningful_feedback_is_accepted():
    result = evaluate_feedback_quality("very bad service")

    assert result.should_analyze is True
    assert result.quality_score == 0.5


def test_detailed_feedback_gets_higher_quality_score():
    result = evaluate_feedback_quality(
        "delivery was late and my ice cream arrived completely melted"
    )

    assert result.should_analyze is True
    assert result.quality_score == 0.75

def test_non_english_feedback_is_not_rejected():
    result = evaluate_feedback_quality(
        "मेरा ऑर्डर बहुत देर से आया और खाना ठंडा था"
    )

    assert result.should_analyze is True
    assert result.quality_score > 0