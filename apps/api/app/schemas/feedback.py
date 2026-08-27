from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeedbackIngest(BaseModel):
    external_id: str | None = None

    text: str = Field(
        min_length=1,
        max_length=20_000,
    )

    rating: int | None = None

    source_created_at: datetime | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)