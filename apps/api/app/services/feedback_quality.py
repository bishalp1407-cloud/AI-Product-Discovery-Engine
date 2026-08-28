import re
from dataclasses import dataclass


@dataclass
class QualityResult:
    should_analyze: bool
    quality_score: float
    reason: str | None = None


def evaluate_feedback_quality(text: str | None) -> QualityResult:
    if not text:
        return QualityResult(
            should_analyze=False,
            quality_score=0.0,
            reason="empty_text",
        )

    cleaned = text.strip()

    if not cleaned:
        return QualityResult(
            should_analyze=False,
            quality_score=0.0,
            reason="empty_text",
        )

    # Remove punctuation, emojis and other non-alphanumeric characters.
    meaningful_text = "".join(
        char for char in cleaned
        if char.isalnum() or char.isspace()
    ).strip()

    if not meaningful_text:
        return QualityResult(
            should_analyze=False,
            quality_score=0.0,
            reason="no_meaningful_text",
        )

    words = meaningful_text.split()
    word_count = len(words)

    if word_count <= 2:
        return QualityResult(
            should_analyze=False,
            quality_score=0.2,
            reason="too_short",
        )

    if word_count <= 5:
        return QualityResult(
            should_analyze=True,
            quality_score=0.5,
        )

    if word_count <= 15:
        return QualityResult(
            should_analyze=True,
            quality_score=0.75,
        )

    return QualityResult(
        should_analyze=True,
        quality_score=1.0,
    )