from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.feedback_analysis import (
    AnalysisStatus,
    FeedbackAnalysis,
)
from app.models.feedback_source import FeedbackSource
from app.models.insight import Insight
from app.models.insight_feedback import InsightFeedback

# IMPORTANT:
# Project must be imported so SQLAlchemy metadata knows about
# the "projects" table when resolving Insight.project_id.
from app.models.project import Project  # noqa: F401

from app.services.embedding_service import generate_embeddings
from app.services.insight_generation_service import (
    CandidateCluster,
    cluster_candidate_issues,
    get_candidate_issues,
)
from app.services.insight_scoring_service import (
    InsightScores,
    calculate_cohesion_score,
    calculate_insight_scores,
)
from app.services.insight_summary_service import (
    GeneratedInsight,
    generate_fallback_insight_summary,
    generate_insight_summaries_batch,
)


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

MINIMUM_EVIDENCE_COUNT = 2

# Only the highest-ranked insights receive AI-generated wording.
AI_ENRICHMENT_LIMIT = 15

# 15 enriched insights / batch size 5 = maximum 3 batch requests.
AI_SUMMARY_BATCH_SIZE = 5


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------


@dataclass
class PreparedInsight:
    """
    Fully generated and scored insight that has not yet
    been persisted to PostgreSQL.
    """

    cluster: CandidateCluster
    summary: GeneratedInsight
    scores: InsightScores


@dataclass
class InsightEngineResult:
    """
    Summary returned after a successful project insight
    rebuild.
    """

    project_id: UUID
    candidate_count: int
    cluster_count: int
    recurring_cluster_count: int
    persisted_insight_count: int
    total_relevant_feedback: int


# ------------------------------------------------------------------
# Source normalization
# ------------------------------------------------------------------


def _normalize_source_type(
    source_type: object,
) -> str:
    """
    Convert SQLAlchemy/Python enum values into stable
    domain values such as:

        google_play
        app_store
        youtube

    instead of strings such as:

        SourceType.GOOGLE_PLAY
    """

    if hasattr(source_type, "value"):
        return str(source_type.value)

    return str(source_type)


# ------------------------------------------------------------------
# Project-scoped metrics
# ------------------------------------------------------------------


def _get_total_relevant_feedback(
    db: Session,
    *,
    project_id: UUID,
) -> int:
    """
    Count relevant completed v3 analyses for ONE project.

    Project scoping here is critical because Reach is:

        cluster feedback count
        ----------------------
        project's relevant feedback

    Another project's feedback must never affect this
    denominator.

    Note:
    Positive relevant feedback remains part of this
    denominator even though positive feedback is excluded
    from problem-candidate generation.

    This keeps Reach expressed as prevalence among all
    relevant analyzed feedback rather than only complaints.
    """

    statement = (
        select(
            func.count(FeedbackAnalysis.id)
        )
        .join(
            Feedback,
            Feedback.id
            == FeedbackAnalysis.feedback_id,
        )
        .where(
            Feedback.project_id == project_id,
            FeedbackAnalysis.prompt_version
            == "v3",
            FeedbackAnalysis.analysis_status
            == AnalysisStatus.COMPLETED,
            FeedbackAnalysis.is_relevant.is_(
                True
            ),
        )
    )

    return int(
        db.scalar(statement)
        or 0
    )


def _get_available_source_types(
    db: Session,
    *,
    project_id: UUID,
) -> set[str]:
    """
    Return the logical feedback channels configured for
    this project.

    We intentionally use source TYPE rather than source ID.

    Example:

        {"google_play", "app_store", "youtube"}

    This prevents multiple connectors of the same logical
    channel from artificially increasing source diversity.
    """

    statement = (
        select(
            FeedbackSource.source_type
        )
        .where(
            FeedbackSource.project_id
            == project_id
        )
        .distinct()
    )

    source_types = db.scalars(
        statement
    ).all()

    return {
        _normalize_source_type(
            source_type
        )
        for source_type in source_types
    }


# ------------------------------------------------------------------
# Cohesion
# ------------------------------------------------------------------


def _calculate_cluster_cohesion(
    cluster: CandidateCluster,
) -> float:
    """
    Re-embed the cluster's pain points and calculate
    average pairwise semantic similarity.

    The clustering step already embeds these texts, so
    this duplicates some local computation.

    For the MVP this is acceptable because MiniLM runs
    locally and the dataset is small.

    A future optimization can reuse/cache embeddings
    between clustering and scoring.
    """

    pain_points = [
        member.pain_point
        for member in cluster.members
    ]

    if not pain_points:
        return 0.0

    embedding_results = generate_embeddings(
        pain_points
    )

    embeddings = [
        result.embedding
        for result in embedding_results
    ]

    return calculate_cohesion_score(
        embeddings
    )


# ------------------------------------------------------------------
# Scoring
# ------------------------------------------------------------------


def _score_cluster(
    cluster: CandidateCluster,
    *,
    total_relevant_feedback: int,
    available_source_types: set[str],
) -> InsightScores:
    """
    Calculate modified RICE-style discovery scoring:

        Opportunity Score
            =
        Reach × Impact × Confidence

    Effort is intentionally excluded because these are
    discovered problems, not proposed solutions.
    """

    severities = [
        member.severity
        for member in cluster.members
    ]

    supporting_source_types = {
        member.source_type
        for member in cluster.members
    }

    cohesion_score = (
        _calculate_cluster_cohesion(
            cluster
        )
    )

    return calculate_insight_scores(
        feedback_count=len(
            cluster.members
        ),
        total_relevant_feedback=(
            total_relevant_feedback
        ),
        severities=severities,
        cohesion_score=cohesion_score,
        supporting_source_types=(
            supporting_source_types
        ),
        available_source_types=(
            available_source_types
        ),
    )


# ------------------------------------------------------------------
# Insight preparation
# ------------------------------------------------------------------


def _prepare_insights(
    clusters: list[CandidateCluster],
    *,
    total_relevant_feedback: int,
    available_source_types: set[str],
) -> list[PreparedInsight]:
    """
    Prepare recurring product insights for persistence.

    Pipeline:

        recurring clusters
              ↓
        deterministic scoring
              ↓
        opportunity ranking
              ↓
        top N -> batched AI enrichment
        rest  -> deterministic summaries
              ↓
        persistence

    AI affects presentation only, never ranking.

    With the current MVP configuration:

        AI_ENRICHMENT_LIMIT = 15
        AI_SUMMARY_BATCH_SIZE = 5

    therefore at most three batch-generation requests
    are needed.
    """

    scored_clusters: list[
        tuple[
            CandidateCluster,
            InsightScores,
        ]
    ] = []

    # ----------------------------------------------------------
    # 1. Score every recurring cluster deterministically.
    # ----------------------------------------------------------

    for cluster in clusters:
        if (
            len(cluster.members)
            < MINIMUM_EVIDENCE_COUNT
        ):
            continue

        scores = _score_cluster(
            cluster,
            total_relevant_feedback=(
                total_relevant_feedback
            ),
            available_source_types=(
                available_source_types
            ),
        )

        scored_clusters.append(
            (
                cluster,
                scores,
            )
        )

    # ----------------------------------------------------------
    # 2. Rank BEFORE consuming external AI capacity.
    # ----------------------------------------------------------

    scored_clusters.sort(
        key=lambda item: (
            item[1].opportunity_score
        ),
        reverse=True,
    )

    prepared: list[PreparedInsight] = []

    enrichment_count = min(
        AI_ENRICHMENT_LIMIT,
        len(scored_clusters),
    )

    # ----------------------------------------------------------
    # 3. AI-enrich only the highest-priority clusters.
    #
    # Current configuration:
    #
    # 15 insights / batch size 5
    # = maximum 3 batch requests.
    #
    # If a batch fails, the batch-summary service returns
    # deterministic summaries for that batch.
    # ----------------------------------------------------------

    for start in range(
        0,
        enrichment_count,
        AI_SUMMARY_BATCH_SIZE,
    ):
        end = min(
            start + AI_SUMMARY_BATCH_SIZE,
            enrichment_count,
        )

        batch_items = scored_clusters[
            start:end
        ]

        batch_clusters = [
            cluster
            for cluster, _ in batch_items
        ]

        batch_summaries = (
            generate_insight_summaries_batch(
                batch_clusters
            )
        )

        # The batch-summary service guarantees one returned
        # summary for every supplied cluster, using fallback
        # summaries where necessary.
        for (
            cluster,
            scores,
        ), summary in zip(
            batch_items,
            batch_summaries,
        ):
            prepared.append(
                PreparedInsight(
                    cluster=cluster,
                    summary=summary,
                    scores=scores,
                )
            )

    # ----------------------------------------------------------
    # 4. Remaining lower-ranked clusters use deterministic
    #    summaries and require no external provider call.
    # ----------------------------------------------------------

    for cluster, scores in scored_clusters[
        enrichment_count:
    ]:
        summary = (
            generate_fallback_insight_summary(
                cluster
            )
        )

        prepared.append(
            PreparedInsight(
                cluster=cluster,
                summary=summary,
                scores=scores,
            )
        )

    return prepared


# ------------------------------------------------------------------
# Persistence
# ------------------------------------------------------------------


def _replace_project_insights(
    db: Session,
    *,
    project_id: UUID,
    prepared_insights: list[
        PreparedInsight
    ],
) -> int:
    """
    Replace derived insights for ONE project.

    MVP idempotency strategy:

        regenerate project
            ↓
        delete old derived insights
            ↓
        insert fresh derived insights

    This avoids duplicate insight rows when the engine is
    rerun.

    InsightFeedback rows are removed through the database
    ON DELETE CASCADE relationship.

    Important transaction property:

    Generation and scoring happen before this function is
    called. Therefore external AI/provider failures cannot
    delete the project's existing insights before the new
    insight set has been prepared.
    """

    db.execute(
        delete(Insight).where(
            Insight.project_id
            == project_id
        )
    )

    persisted_count = 0

    for prepared in prepared_insights:
        insight = Insight(
            project_id=project_id,
            category=prepared.cluster.category,
            title=prepared.summary.title,
            description=prepared.summary.description,
            feedback_count=prepared.scores.feedback_count,
            reach_score=prepared.scores.reach_score,
            impact_score=prepared.scores.impact_score,
            confidence_score=prepared.scores.confidence_score,
            opportunity_score=prepared.scores.opportunity_score,
        )

        db.add(insight)

        # Generate the insight UUID before creating
        # evidence links.
        db.flush()

        # A cluster should contain each feedback record only once.
        # Keep this guard at the persistence boundary so duplicate
        # members cannot violate the composite primary key on
        # (insight_id, feedback_id).
        seen_feedback_ids: set[UUID] = set()

        for member in prepared.cluster.members:
            feedback_id = UUID(member.feedback_id)

            if feedback_id in seen_feedback_ids:
                continue

            seen_feedback_ids.add(feedback_id)

            evidence_link = InsightFeedback(
                insight_id=insight.id,
                feedback_id=feedback_id,
            )

            db.add(evidence_link)

        persisted_count += 1

    return persisted_count
# ------------------------------------------------------------------
# Public Insight Engine
# ------------------------------------------------------------------


def rebuild_project_insights(
    db: Session,
    *,
    project_id: UUID,
) -> InsightEngineResult:
    """
    Rebuild all recurring product insights for one project.

    End-to-end M5 pipeline:

        project feedback
            ↓
        relevant v3 analyses
            ↓
        problem-candidate filtering
            ↓
        category-first semantic clustering
            ↓
        recurring clusters
            ↓
        deterministic scoring
            ↓
        opportunity ranking
            ↓
        batched AI enrichment for top insights
            ↓
        deterministic fallback where necessary
            ↓
        project-scoped persistence

    The caller owns the Session object, but this service
    owns commit/rollback for the rebuild operation.

    AI/provider availability must never control clustering,
    scoring, ranking, evidence linking, or whether the
    Insight Engine can ultimately produce an insight set.
    """

    try:
        # ------------------------------------------------------
        # 1. Load project-scoped discovery inputs
        # ------------------------------------------------------

        candidates = get_candidate_issues(
            db,
            project_id=project_id,
        )

        total_relevant_feedback = (
            _get_total_relevant_feedback(
                db,
                project_id=project_id,
            )
        )

        available_source_types = (
            _get_available_source_types(
                db,
                project_id=project_id,
            )
        )

        # ------------------------------------------------------
        # End the read transaction before long-running
        # clustering and AI enrichment.
        #
        # The data above has already been materialized into
        # plain Python values/dataclasses, so it does not need
        # an active database transaction anymore.
        #
        # Persistence below will automatically begin a fresh
        # transaction for the atomic DELETE + INSERT operation.
        # ------------------------------------------------------

        db.rollback()

        # ------------------------------------------------------
        # 2. Semantic clustering
        # ------------------------------------------------------

        clusters = (
            cluster_candidate_issues(
                candidates
            )
        )

        recurring_clusters = [
            cluster
            for cluster in clusters
            if len(cluster.members)
            >= MINIMUM_EVIDENCE_COUNT
        ]

        # ------------------------------------------------------
        # 3. Score + rank + generate summaries in memory
        # ------------------------------------------------------

        prepared_insights = (
            _prepare_insights(
                recurring_clusters,
                total_relevant_feedback=(
                    total_relevant_feedback
                ),
                available_source_types=(
                    available_source_types
                ),
            )
        )

        # ------------------------------------------------------
        # 4. Replace derived insights for this project only
        # ------------------------------------------------------

        persisted_count = (
            _replace_project_insights(
                db,
                project_id=project_id,
                prepared_insights=(
                    prepared_insights
                ),
            )
        )

        # ------------------------------------------------------
        # 5. Commit atomically
        # ------------------------------------------------------

        db.commit()

        return InsightEngineResult(
            project_id=project_id,
            candidate_count=len(
                candidates
            ),
            cluster_count=len(
                clusters
            ),
            recurring_cluster_count=len(
                recurring_clusters
            ),
            persisted_insight_count=(
                persisted_count
            ),
            total_relevant_feedback=(
                total_relevant_feedback
            ),
        )

    except Exception:
        # If persistence fails at any point, restore the
        # transaction rather than leaving a partial insight set.
        db.rollback()
        raise