from pydantic import BaseModel, Field


class InsightSummaryResult(BaseModel):
    title: str = Field(
        min_length=5,
        max_length=100,
    )
    description: str = Field(
        min_length=10,
        max_length=350,
    )


class BatchInsightSummaryItem(
    InsightSummaryResult
):
    cluster_id: int = Field(ge=0)


class BatchInsightSummaryResult(BaseModel):
    insights: list[BatchInsightSummaryItem]