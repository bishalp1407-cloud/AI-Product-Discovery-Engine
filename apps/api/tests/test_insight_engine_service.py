from unittest.mock import MagicMock
from uuid import uuid4

from app.models.insight_feedback import InsightFeedback
from app.services.insight_engine_service import (
    PreparedInsight,
    _replace_project_insights,
)
from app.services.insight_generation_service import (
    CandidateCluster,
    CandidateIssue,
)
from app.services.insight_scoring_service import InsightScores
from app.services.insight_summary_service import GeneratedInsight


def test_replace_project_insights_deduplicates_evidence_links():
    project_id = uuid4()
    feedback_id = uuid4()
    generated_insight_id = uuid4()

    duplicate_member = CandidateIssue(
        feedback_id=str(feedback_id),
        source_type="google_play",
        category="delivery",
        pain_point="Delivery was late",
        severity="medium",
    )

    cluster = CandidateCluster(
        category="delivery",
        members=[
            duplicate_member,
            duplicate_member,
        ],
    )

    summary = GeneratedInsight(
        title="Late deliveries",
        description="Users report deliveries arriving late.",
        generation_method="deterministic",
    )

    scores = InsightScores(
        feedback_count=2,
        reach_score=0.5,
        impact_score=2.0,
        volume_score=0.4,
        cohesion_score=1.0,
        diversity_score=0.2,
        confidence_score=0.64,
        opportunity_score=0.64,
    )

    prepared = PreparedInsight(
        cluster=cluster,
        summary=summary,
        scores=scores,
    )

    db = MagicMock()

    # _replace_project_insights calls db.flush() after adding
    # the Insight so its generated UUID can be used by evidence
    # relationships. Simulate that database-generated UUID.
    def assign_insight_id():
        for call in db.add.call_args_list:
            obj = call.args[0]

            if not isinstance(obj, InsightFeedback):
                obj.id = generated_insight_id

    db.flush.side_effect = assign_insight_id

    persisted_count = _replace_project_insights(
        db,
        project_id=project_id,
        prepared_insights=[prepared],
    )

    evidence_links = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], InsightFeedback)
    ]

    assert persisted_count == 1
    assert len(evidence_links) == 1
    assert evidence_links[0].insight_id == generated_insight_id
    assert evidence_links[0].feedback_id == feedback_id