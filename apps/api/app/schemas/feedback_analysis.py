from typing import Literal

from pydantic import BaseModel, Field


FeedbackCategory = Literal[
    "ordering",
    "delivery",
    "payments_refunds",
    "product_quality",
    "pricing_fees",
    "availability",
    "customer_support",
    "app_usability",
    "account",
    "promotions",
    "packaging",
    "general_experience",
    "employment",
    "video_discussion",
    "market_opinion",
    "unrelated",
]


class FeedbackAnalysisResult(BaseModel):
    is_relevant: bool = Field(
        description=(
            "Whether the feedback is relevant to "
            "customer product experience."
        )
    )

    sentiment: Literal[
        "positive",
        "neutral",
        "negative",
    ] = Field(
        description="Overall sentiment of the feedback."
    )

    category: FeedbackCategory = Field(
        description=(
            "Controlled category describing the primary "
            "topic of the feedback."
        )
    )

    pain_point: str = Field(
        description=(
            "The main user pain point expressed "
            "in the feedback."
        )
    )

    severity: Literal[
        "low",
        "medium",
        "high",
    ] = Field(
        description="Severity of the user's pain point."
    )

    summary: str = Field(
        description=(
            "Concise summary of the feedback "
            "in one sentence."
        )
    )