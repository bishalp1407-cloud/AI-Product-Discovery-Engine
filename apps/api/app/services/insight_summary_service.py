import json
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.schemas.insight_summary import (
    BatchInsightSummaryResult,
    InsightSummaryResult,
)
from app.services.insight_generation_service import (
    CandidateCluster,
)
from app.services.openrouter_client import (
    repair_common_json_issues,
    request_openrouter_completion,
)


@dataclass
class GeneratedInsight:
    title: str
    description: str
    generation_method: str


# ------------------------------------------------------------------
# Deterministic fallback
# ------------------------------------------------------------------


def _clean_text(text: str) -> str:
    """
    Normalize whitespace without changing semantic meaning.
    """
    return " ".join(
        text.strip().split()
    ).rstrip(". ")


def _select_representative_pain_point(
    cluster: CandidateCluster,
) -> str:
    """
    Select a deterministic representative pain point.

    MVP fallback strategy:
    choose the pain point closest to the average text length.

    This is used only when AI generation and repair fail.
    """
    if not cluster.members:
        return ""

    pain_points = [
        _clean_text(member.pain_point)
        for member in cluster.members
        if member.pain_point.strip()
    ]

    if not pain_points:
        return ""

    average_length = sum(
        len(text)
        for text in pain_points
    ) / len(pain_points)

    return min(
        pain_points,
        key=lambda text: abs(
            len(text) - average_length
        ),
    )


def _build_fallback_title(
    cluster: CandidateCluster,
) -> str:
    representative = (
        _select_representative_pain_point(
            cluster
        )
    )

    if not representative:
        return "Unspecified customer problem"

    max_length = 100

    if len(representative) > max_length:
        shortened = representative[
            :max_length
        ]

        if " " in shortened:
            shortened = shortened.rsplit(
                " ",
                1,
            )[0]

        representative = shortened.rstrip(
            ",;:- "
        )

    return (
        representative[0].upper()
        + representative[1:]
    )


def _build_fallback_description(
    cluster: CandidateCluster,
) -> str:
    feedback_count = len(
        cluster.members
    )

    if feedback_count == 0:
        return (
            "No supporting feedback is available "
            "for this issue."
        )

    representative = (
        _select_representative_pain_point(
            cluster
        )
    )

    category = cluster.category.replace(
        "_",
        " ",
    )

    description = (
        f"{feedback_count} feedback item"
        f"{'s' if feedback_count != 1 else ''} "
        f"in the {category} category describe "
        f"a recurring problem: {representative}."
    )

    if len(description) > 350:
        description = description[:350]

        if " " in description:
            description = description.rsplit(
                " ",
                1,
            )[0]

        description = (
            description.rstrip(
                ",;:-. "
            )
            + "."
        )

    return description


def generate_fallback_insight_summary(
    cluster: CandidateCluster,
) -> GeneratedInsight:
    """
    Deterministic evidence-grounded fallback.
    """
    return GeneratedInsight(
        title=_build_fallback_title(
            cluster
        ),
        description=(
            _build_fallback_description(
                cluster
            )
        ),
        generation_method=(
            "deterministic_fallback"
        ),
    )


# ------------------------------------------------------------------
# Single-insight generation prompts
# ------------------------------------------------------------------


def _build_insight_system_prompt() -> str:
    return """
You are a product insights analyst.

Your task is to synthesize customer problem evidence that
has already been grouped into one candidate product issue.

Return ONLY valid JSON with exactly these fields:

{
  "title": "concise product problem statement",
  "description": "concise evidence-grounded explanation"
}

TITLE RULES:

- Maximum 100 characters.
- Describe the shared customer problem.
- Synthesize the semantic intersection of the evidence.
- Do not simply copy one feedback item when a clearer
  normalized problem statement can be written.
- Write the title as a product problem, not a solution.
- Do not propose features, fixes, or recommendations.
- Do not state a root cause unless the supplied evidence
  explicitly establishes that root cause.
- Do not include feedback counts, scores, percentages,
  category names, or severity labels.
- Avoid unnecessary emotional wording.

DESCRIPTION RULES:

- Maximum 350 characters.
- Explain the shared problem represented by the evidence.
- Use only facts supported by the supplied evidence.
- Prefer facts shared across multiple evidence items.
- A detail appearing in only some evidence may be mentioned
  only when clearly qualified.
- Do not invent technical causes.
- Do not recommend solutions.
- Do not invent frequencies, percentages, customer counts,
  or business impact.

EVIDENCE BOUNDARY RULES:

- Do not generalize beyond the supplied evidence.
- Do not transform a few specific examples into a broad
  platform-wide claim.
- If two specific payment methods have reported problems,
  describe problems with those methods. Do not infer that
  the entire payment system is unreliable.
- Do not infer business consequences such as churn,
  retention loss, revenue impact, reduced conversion,
  or loss of customer trust unless directly established
  by the evidence.
- Do not infer customer intent.
- Do not infer why the problem happens.
- When evidence contains partially related details,
  summarize only the strongest common problem.
- When details conflict, omit the conflicting detail rather
  than attempting to reconcile it through speculation.

STYLE:

- Be concise.
- Be neutral.
- Be specific.
- Use plain product language.
- Do not include markdown.
- Do not include explanations outside the JSON.
""".strip()


def _build_insight_user_prompt(
    cluster: CandidateCluster,
) -> str:
    evidence_lines = []

    for index, member in enumerate(
        cluster.members,
        start=1,
    ):
        evidence_lines.append(
            f"{index}. "
            f"[severity={member.severity}] "
            f"{member.pain_point}"
        )

    evidence = "\n".join(
        evidence_lines
    )

    return (
        f"Category: {cluster.category}\n\n"
        "Supporting evidence:\n"
        f"{evidence}"
    )


# ------------------------------------------------------------------
# Single-insight parsing
# ------------------------------------------------------------------


def _parse_insight_response(
    content: str,
) -> InsightSummaryResult:
    """
    Parse and validate structured AI output.
    """
    try:
        parsed = json.loads(
            content
        )

    except json.JSONDecodeError:
        repaired_content = (
            repair_common_json_issues(
                content
            )
        )

        parsed = json.loads(
            repaired_content
        )

    return InsightSummaryResult.model_validate(
        parsed
    )


# ------------------------------------------------------------------
# Single-insight repair
# ------------------------------------------------------------------


def _build_repair_system_prompt() -> str:
    return """
You are repairing a product insight that failed structured
output validation.

Return ONLY valid JSON with exactly:

{
  "title": "...",
  "description": "..."
}

Requirements:

- title must be between 5 and 100 characters
- description must be between 10 and 350 characters
- preserve only claims supported by the original evidence
- remove unsupported generalizations
- remove inferred root causes
- remove inferred business consequences
- remove proposed solutions
- make the result concise
- do not add new facts
- do not include markdown
- do not include text outside the JSON
""".strip()


def _build_repair_user_prompt(
    *,
    cluster: CandidateCluster,
    invalid_content: str,
) -> str:
    evidence_lines = []

    for index, member in enumerate(
        cluster.members,
        start=1,
    ):
        evidence_lines.append(
            f"{index}. {member.pain_point}"
        )

    evidence = "\n".join(
        evidence_lines
    )

    return (
        "ORIGINAL EVIDENCE:\n"
        f"{evidence}\n\n"
        "INVALID GENERATED OUTPUT:\n"
        f"{invalid_content}\n\n"
        "Repair the generated output while remaining "
        "strictly grounded in the original evidence."
    )


def _attempt_repair(
    *,
    cluster: CandidateCluster,
    invalid_content: str,
) -> InsightSummaryResult:
    """
    Give the model one constrained opportunity to repair
    invalid structured output.
    """
    repaired_content = (
        request_openrouter_completion(
            system_prompt=(
                _build_repair_system_prompt()
            ),
            user_prompt=(
                _build_repair_user_prompt(
                    cluster=cluster,
                    invalid_content=(
                        invalid_content
                    ),
                )
            ),
            temperature=0.0,
        )
    )

    return _parse_insight_response(
        repaired_content
    )


# ------------------------------------------------------------------
# Public single-insight generation
# ------------------------------------------------------------------


def generate_insight_summary(
    cluster: CandidateCluster,
) -> GeneratedInsight:
    """
    Generate a human-readable product insight.

    The language model controls wording only.

    It does NOT control:
    - clustering
    - reach
    - impact
    - confidence
    - opportunity score
    - ranking
    - persistence
    """
    if not cluster.members:
        return generate_fallback_insight_summary(
            cluster
        )

    content: str | None = None

    # Primary generation
    try:
        content = (
            request_openrouter_completion(
                system_prompt=(
                    _build_insight_system_prompt()
                ),
                user_prompt=(
                    _build_insight_user_prompt(
                        cluster
                    )
                ),
                temperature=0.1,
            )
        )

        result = _parse_insight_response(
            content
        )

        return GeneratedInsight(
            title=result.title.strip(),
            description=(
                result.description.strip()
            ),
            generation_method="openrouter",
        )

    except (
        RuntimeError,
        httpx.HTTPError,
        json.JSONDecodeError,
        ValidationError,
    ) as primary_error:
        print(
            "Primary insight generation failed. "
            "Attempting one repair. "
            f"Reason: {primary_error}"
        )

    # One repair attempt only if content was returned.
    if content is not None:
        try:
            repaired_result = _attempt_repair(
                cluster=cluster,
                invalid_content=content,
            )

            return GeneratedInsight(
                title=(
                    repaired_result.title.strip()
                ),
                description=(
                    repaired_result.description.strip()
                ),
                generation_method=(
                    "openrouter_repaired"
                ),
            )

        except (
            RuntimeError,
            httpx.HTTPError,
            json.JSONDecodeError,
            ValidationError,
        ) as repair_error:
            print(
                "Insight repair failed. "
                "Using deterministic fallback. "
                f"Reason: {repair_error}"
            )

    return generate_fallback_insight_summary(
        cluster
    )


# ------------------------------------------------------------------
# Batch generation prompts
# ------------------------------------------------------------------


def _build_batch_system_prompt() -> str:
    return """
You are a product insights analyst.

You will receive several independent customer-problem
clusters.

Generate exactly one product insight for every cluster.

Return ONLY valid JSON in this structure:

{
  "insights": [
    {
      "cluster_id": 0,
      "title": "...",
      "description": "..."
    }
  ]
}

RULES:

- Preserve the supplied cluster_id exactly.
- Return each cluster_id exactly once.
- Never combine different clusters.
- title must be between 5 and 100 characters.
- description must be between 10 and 350 characters.
- Describe the shared customer problem.
- Synthesize the semantic intersection of each cluster.
- Use only information supported by that cluster's evidence.
- Do not propose solutions.
- Do not infer root causes.
- Do not infer churn, revenue impact, conversion impact,
  or other business consequences.
- Do not invent frequencies or percentages.
- Do not include scores, categories, severity labels,
  or feedback counts in generated text.
- If evidence contains different details, describe only
  their strongest semantic intersection.
- When evidence conflicts, omit the conflicting detail.
- Do not generalize beyond the supplied evidence.
- Use concise, neutral product language.
- Do not include markdown.
- Return no text outside the JSON.
""".strip()


def _build_batch_user_prompt(
    clusters: list[CandidateCluster],
) -> str:
    sections: list[str] = []

    for cluster_id, cluster in enumerate(
        clusters
    ):
        evidence_lines = []

        for index, member in enumerate(
            cluster.members,
            start=1,
        ):
            evidence_lines.append(
                f"{index}. "
                f"[severity={member.severity}] "
                f"{member.pain_point}"
            )

        evidence = "\n".join(
            evidence_lines
        )

        sections.append(
            f"CLUSTER_ID: {cluster_id}\n"
            f"CATEGORY: {cluster.category}\n"
            "EVIDENCE:\n"
            f"{evidence}"
        )

    return "\n\n---\n\n".join(
        sections
    )


# ------------------------------------------------------------------
# Batch parsing
# ------------------------------------------------------------------


def _parse_batch_response(
    content: str,
) -> BatchInsightSummaryResult:
    """
    Parse and validate a batch response.
    """
    try:
        parsed = json.loads(
            content
        )

    except json.JSONDecodeError:
        repaired_content = (
            repair_common_json_issues(
                content
            )
        )

        parsed = json.loads(
            repaired_content
        )

    return (
        BatchInsightSummaryResult
        .model_validate(parsed)
    )


# ------------------------------------------------------------------
# Public batch generation
# ------------------------------------------------------------------


def generate_insight_summaries_batch(
    clusters: list[CandidateCluster],
) -> list[GeneratedInsight]:
    """
    Generate summaries for several clusters using one
    OpenRouter request.

    Failure policy:

    - valid AI item -> use AI summary
    - missing item -> deterministic fallback
    - duplicate ID -> deterministic fallback
    - invalid ID -> ignore it
    - provider failure -> fallback entire batch
    - malformed batch -> fallback entire batch

    Batch generation intentionally performs no second
    LLM repair request. This prevents a rate-limited
    provider from multiplying API calls.
    """
    if not clusters:
        return []

    fallbacks = [
        generate_fallback_insight_summary(
            cluster
        )
        for cluster in clusters
    ]

    try:
        content = (
            request_openrouter_completion(
                system_prompt=(
                    _build_batch_system_prompt()
                ),
                user_prompt=(
                    _build_batch_user_prompt(
                        clusters
                    )
                ),
                temperature=0.1,
            )
        )

        result = _parse_batch_response(
            content
        )

    except (
        RuntimeError,
        httpx.HTTPError,
        json.JSONDecodeError,
        ValidationError,
    ) as error:
        print(
            "Batch insight generation failed. "
            "Using deterministic fallback for "
            f"{len(clusters)} clusters. "
            f"Reason: {error}"
        )

        return fallbacks

    # Explicit ID mapping prevents us from assuming
    # that the LLM preserved response ordering.
    generated_by_id: dict[
        int,
        GeneratedInsight,
    ] = {}

    duplicate_ids: set[int] = set()

    for item in result.insights:
        cluster_id = item.cluster_id

        # Ignore IDs that do not correspond to a
        # cluster in the current batch.
        if not (
            0
            <= cluster_id
            < len(clusters)
        ):
            continue

        # If an ID occurs more than once, we cannot
        # safely decide which generated result is valid.
        if cluster_id in generated_by_id:
            duplicate_ids.add(
                cluster_id
            )
            continue

        generated_by_id[
            cluster_id
        ] = GeneratedInsight(
            title=item.title.strip(),
            description=(
                item.description.strip()
            ),
            generation_method=(
                "openrouter_batch"
            ),
        )

    # Force duplicate IDs to deterministic fallback.
    for cluster_id in duplicate_ids:
        generated_by_id.pop(
            cluster_id,
            None,
        )

    summaries: list[
        GeneratedInsight
    ] = []

    # Preserve original cluster order for orchestration.
    for cluster_id in range(
        len(clusters)
    ):
        summaries.append(
            generated_by_id.get(
                cluster_id,
                fallbacks[cluster_id],
            )
        )

    return summaries