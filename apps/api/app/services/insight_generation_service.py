from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sklearn.cluster import AgglomerativeClustering

from app.models.feedback import Feedback
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
    Sentiment,
)
from app.models.feedback_source import FeedbackSource
from app.services.embedding_service import generate_embeddings


# MVP default calibrated on the current Blinkit dataset.
# This is NOT a universal threshold and should remain configurable.
DEFAULT_SIMILARITY_THRESHOLD = 0.62


PLACEHOLDER_PAIN_POINTS = {
    "",
    "none",
    "n/a",
    "na",
    "null",
    "no pain point",
    "not applicable",
}


@dataclass
class CandidateIssue:
    feedback_id: str
    source_type: str
    category: str
    pain_point: str
    severity: str


@dataclass
class CandidateCluster:
    category: str
    members: list[CandidateIssue]


def get_candidate_issues(
    db: Session,
    project_id: UUID,
) -> list[CandidateIssue]:
    """
    Return usable problem evidence for a specific project
    from completed v3 analyses.

    Only relevant feedback with a non-placeholder pain point
    becomes a candidate issue.

    Project scoping prevents feedback from different projects
    from being mixed during insight generation.
    """

    rows = db.execute(
        select(
            Feedback.id,
            FeedbackSource.source_type,
            FeedbackAnalysis.category,
            FeedbackAnalysis.pain_point,
            FeedbackAnalysis.severity,
        )
        .join(
            FeedbackAnalysis,
            FeedbackAnalysis.feedback_id
            == Feedback.id,
        )
        .join(
            FeedbackSource,
            FeedbackSource.id
            == Feedback.source_id,
        )
        .where(
            Feedback.project_id == project_id,
            FeedbackAnalysis.prompt_version == "v3",
            FeedbackAnalysis.analysis_status
            == AnalysisStatus.COMPLETED,
            FeedbackAnalysis.is_relevant.is_(True),
            FeedbackAnalysis.pain_point.is_not(None),
            FeedbackAnalysis.sentiment
            != Sentiment.POSITIVE,
        )
    ).all()

    candidates: list[CandidateIssue] = []

    for (
        feedback_id,
        source_type,
        category,
        pain_point,
        severity,
    ) in rows:
        cleaned_pain_point = pain_point.strip()

        if (
            cleaned_pain_point.lower()
            in PLACEHOLDER_PAIN_POINTS
        ):
            continue

        candidates.append(
            CandidateIssue(
                feedback_id=str(feedback_id),
                source_type=(
                    source_type.value
                    if hasattr(source_type, "value")
                    else str(source_type)
                ),
                category=category,
                pain_point=cleaned_pain_point,
                severity=(
                    severity.value
                    if severity is not None
                    else "low"
                ),
            )
        )

    return candidates


def cluster_candidate_issues(
    candidates: list[CandidateIssue],
    similarity_threshold: float = (
        DEFAULT_SIMILARITY_THRESHOLD
    ),
) -> list[CandidateCluster]:
    """
    Cluster candidate issues within their controlled M4 category.

    Uses:
    - local MiniLM embeddings
    - cosine distance
    - average-linkage agglomerative clustering

    The similarity threshold is an MVP default calibrated on
    the current dataset and should not be treated as universal.
    """

    if not candidates:
        return []

    categories: dict[
        str,
        list[CandidateIssue],
    ] = {}

    # Never cluster candidates from different controlled
    # M4 categories together.
    for candidate in candidates:
        categories.setdefault(
            candidate.category,
            [],
        ).append(candidate)

    final_clusters: list[CandidateCluster] = []

    for (
        category,
        category_candidates,
    ) in categories.items():

        # A category containing only one candidate cannot
        # produce a recurring issue, but we still return it
        # as a singleton cluster for downstream inspection.
        if len(category_candidates) == 1:
            final_clusters.append(
                CandidateCluster(
                    category=category,
                    members=category_candidates,
                )
            )
            continue

        texts = [
            candidate.pain_point
            for candidate in category_candidates
        ]

        embedding_results = generate_embeddings(
            texts
        )

        vectors = [
            result.embedding
            for result in embedding_results
        ]

        # cosine_distance = 1 - cosine_similarity
        distance_threshold = (
            1.0 - similarity_threshold
        )

        model = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=distance_threshold,
        )

        labels = model.fit_predict(
            vectors
        )

        grouped: dict[
            int,
            list[CandidateIssue],
        ] = {}

        for (
            candidate,
            label,
        ) in zip(
            category_candidates,
            labels,
        ):
            grouped.setdefault(
                int(label),
                [],
            ).append(candidate)

        for members in grouped.values():
            final_clusters.append(
                CandidateCluster(
                    category=category,
                    members=members,
                )
            )

    return final_clusters