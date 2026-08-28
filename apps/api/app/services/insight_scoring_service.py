from dataclasses import dataclass


SEVERITY_WEIGHTS = {
    "low": 1.0,
    "medium": 2.0,
    "high": 3.0,
}


@dataclass
class InsightScores:
    feedback_count: int
    reach_score: float
    impact_score: float
    volume_score: float
    cohesion_score: float
    diversity_score: float
    confidence_score: float
    opportunity_score: float


def calculate_volume_score(
    feedback_count: int,
) -> float:
    if feedback_count <= 1:
        return 0.20

    if feedback_count == 2:
        return 0.40

    if feedback_count <= 4:
        return 0.60

    if feedback_count <= 9:
        return 0.80

    return 1.00


def calculate_impact_score(
    severities: list[str],
) -> float:
    if not severities:
        return 0.0

    total = sum(
        SEVERITY_WEIGHTS.get(
            severity.lower(),
            1.0,
        )
        for severity in severities
    )

    return total / len(severities)


def calculate_cohesion_score(
    embeddings: list[list[float]],
) -> float:
    if not embeddings:
        return 0.0

    if len(embeddings) == 1:
        return 1.0

    similarities: list[float] = []

    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            similarity = sum(
                a * b
                for a, b in zip(
                    embeddings[i],
                    embeddings[j],
                )
            )

            similarities.append(
                similarity
            )

    if not similarities:
        return 0.0

    average_similarity = (
        sum(similarities)
        / len(similarities)
    )

    return max(
        0.0,
        min(
            1.0,
            average_similarity,
        ),
    )


def calculate_diversity_score(
    supporting_source_types: set[str],
    available_source_types: set[str],
) -> float:
    if not available_source_types:
        return 0.0

    valid_supporting_sources = (
        supporting_source_types
        & available_source_types
    )

    return (
        len(valid_supporting_sources)
        / len(available_source_types)
    )


def calculate_confidence_score(
    volume_score: float,
    cohesion_score: float,
    diversity_score: float,
) -> float:
    return (
        0.40 * volume_score
        + 0.40 * cohesion_score
        + 0.20 * diversity_score
    )


def calculate_insight_scores(
    *,
    feedback_count: int,
    total_relevant_feedback: int,
    severities: list[str],
    cohesion_score: float,
    supporting_source_types: set[str],
    available_source_types: set[str],
) -> InsightScores:

    if total_relevant_feedback <= 0:
        reach_score = 0.0
    else:
        reach_score = (
            feedback_count
            / total_relevant_feedback
        )

    impact_score = calculate_impact_score(
        severities
    )

    volume_score = calculate_volume_score(
        feedback_count
    )

    diversity_score = calculate_diversity_score(
        supporting_source_types,
        available_source_types,
    )

    confidence_score = calculate_confidence_score(
        volume_score,
        cohesion_score,
        diversity_score,
    )

    opportunity_score = (
        reach_score
        * impact_score
        * confidence_score
    )

    return InsightScores(
        feedback_count=feedback_count,
        reach_score=reach_score,
        impact_score=impact_score,
        volume_score=volume_score,
        cohesion_score=cohesion_score,
        diversity_score=diversity_score,
        confidence_score=confidence_score,
        opportunity_score=opportunity_score,
    )