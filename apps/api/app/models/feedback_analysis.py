import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class FeedbackAnalysis(Base):
    __tablename__ = "feedback_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feedback.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_relevant: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    sentiment: Mapped[Sentiment | None] = mapped_column(
        Enum(Sentiment, name="feedback_sentiment"),
        nullable=True,
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    pain_point: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    severity: Mapped[Severity | None] = mapped_column(
        Enum(Severity, name="feedback_severity"),
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    model_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        nullable=False,
        default=AnalysisStatus.PENDING,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )