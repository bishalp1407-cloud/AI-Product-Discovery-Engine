import pytest

from app.services.insight_scoring_service import (
    calculate_cohesion_score,
    calculate_confidence_score,
    calculate_diversity_score,
    calculate_impact_score,
    calculate_insight_scores,
    calculate_volume_score,
)


# ------------------------------------------------------------------
# Volume
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("feedback_count", "expected"),
    [
        (0, 0.20),
        (1, 0.20),
        (2, 0.40),
        (3, 0.60),
        (4, 0.60),
        (5, 0.80),
        (9, 0.80),
        (10, 1.00),
        (50, 1.00),
    ],
)
def test_calculate_volume_score(
    feedback_count,
    expected,
):
    assert calculate_volume_score(feedback_count) == expected


# ------------------------------------------------------------------
# Impact
# ------------------------------------------------------------------


def test_calculate_impact_score():
    severities = [
        "high",
        "medium",
        "low",
    ]

    score = calculate_impact_score(severities)

    # (3 + 2 + 1) / 3
    assert score == pytest.approx(2.0)


def test_calculate_impact_score_empty():
    assert calculate_impact_score([]) == 0.0


def test_calculate_impact_score_is_case_insensitive():
    severities = [
        "HIGH",
        "Medium",
        "low",
    ]

    score = calculate_impact_score(severities)

    assert score == pytest.approx(2.0)


# ------------------------------------------------------------------
# Diversity
# ------------------------------------------------------------------


def test_calculate_diversity_score_one_of_three_sources():
    score = calculate_diversity_score(
        supporting_source_types={
            "google_play",
        },
        available_source_types={
            "google_play",
            "app_store",
            "youtube",
        },
    )

    assert score == pytest.approx(1 / 3)


def test_calculate_diversity_score_two_of_three_sources():
    score = calculate_diversity_score(
        supporting_source_types={
            "google_play",
            "app_store",
        },
        available_source_types={
            "google_play",
            "app_store",
            "youtube",
        },
    )

    assert score == pytest.approx(2 / 3)


def test_calculate_diversity_score_all_sources():
    score = calculate_diversity_score(
        supporting_source_types={
            "google_play",
            "app_store",
            "youtube",
        },
        available_source_types={
            "google_play",
            "app_store",
            "youtube",
        },
    )

    assert score == pytest.approx(1.0)


def test_calculate_diversity_ignores_unknown_sources():
    score = calculate_diversity_score(
        supporting_source_types={
            "google_play",
            "unknown_source",
        },
        available_source_types={
            "google_play",
            "app_store",
            "youtube",
        },
    )

    assert score == pytest.approx(1 / 3)


def test_calculate_diversity_with_no_available_sources():
    score = calculate_diversity_score(
        supporting_source_types={
            "google_play",
        },
        available_source_types=set(),
    )

    assert score == 0.0


# ------------------------------------------------------------------
# Cohesion
# ------------------------------------------------------------------


def test_calculate_cohesion_score_identical_embeddings():
    embeddings = [
        [1.0, 0.0],
        [1.0, 0.0],
    ]

    score = calculate_cohesion_score(embeddings)

    assert score == pytest.approx(1.0)


def test_calculate_cohesion_score_orthogonal_embeddings():
    embeddings = [
        [1.0, 0.0],
        [0.0, 1.0],
    ]

    score = calculate_cohesion_score(embeddings)

    assert score == pytest.approx(0.0)


def test_calculate_cohesion_score_singleton():
    embeddings = [
        [1.0, 0.0],
    ]

    score = calculate_cohesion_score(embeddings)

    assert score == 1.0


def test_calculate_cohesion_score_empty():
    assert calculate_cohesion_score([]) == 0.0


def test_calculate_cohesion_score_average_pairwise_similarity():
    embeddings = [
        [1.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
    ]

    score = calculate_cohesion_score(embeddings)

    # Pair similarities:
    # 1 ↔ 2 = 1
    # 1 ↔ 3 = 0
    # 2 ↔ 3 = 0
    #
    # Average = 1 / 3

    assert score == pytest.approx(1 / 3)


# ------------------------------------------------------------------
# Confidence
# ------------------------------------------------------------------


def test_calculate_confidence_score():
    score = calculate_confidence_score(
        volume_score=0.60,
        cohesion_score=0.70,
        diversity_score=2 / 3,
    )

    expected = (
        0.40 * 0.60
        + 0.40 * 0.70
        + 0.20 * (2 / 3)
    )

    assert score == pytest.approx(expected)


# ------------------------------------------------------------------
# Full Opportunity Score
# ------------------------------------------------------------------


def test_calculate_insight_scores():
    scores = calculate_insight_scores(
        feedback_count=3,
        total_relevant_feedback=100,
        severities=[
            "high",
            "high",
            "medium",
        ],
        cohesion_score=0.70,
        supporting_source_types={
            "google_play",
            "app_store",
        },
        available_source_types={
            "google_play",
            "app_store",
            "youtube",
        },
    )

    # Reach
    assert scores.reach_score == pytest.approx(
        3 / 100
    )

    # Impact = (3 + 3 + 2) / 3
    assert scores.impact_score == pytest.approx(
        8 / 3
    )

    # 3 feedback items -> volume 0.60
    assert scores.volume_score == pytest.approx(
        0.60
    )

    # Two of three independent source types
    assert scores.diversity_score == pytest.approx(
        2 / 3
    )

    expected_confidence = (
        0.40 * 0.60
        + 0.40 * 0.70
        + 0.20 * (2 / 3)
    )

    assert scores.confidence_score == pytest.approx(
        expected_confidence
    )

    expected_opportunity = (
        (3 / 100)
        * (8 / 3)
        * expected_confidence
    )

    assert scores.opportunity_score == pytest.approx(
        expected_opportunity
    )


def test_calculate_insight_scores_zero_relevant_feedback():
    scores = calculate_insight_scores(
        feedback_count=2,
        total_relevant_feedback=0,
        severities=[
            "high",
            "high",
        ],
        cohesion_score=0.80,
        supporting_source_types={
            "google_play",
        },
        available_source_types={
            "google_play",
            "app_store",
            "youtube",
        },
    )

    assert scores.reach_score == 0.0
    assert scores.opportunity_score == 0.0