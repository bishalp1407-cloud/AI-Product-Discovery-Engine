import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, enum.Enum):
    GOOGLE_PLAY = "google_play"
    APP_STORE = "app_store"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    CSV = "csv"
    OTHER = "other"


class SourceStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    ARCHIVED = "archived"


class FeedbackSource(Base):
    __tablename__ = "feedback_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_type: Mapped[SourceType] = mapped_column(
        Enum(
            SourceType,
            name="source_type_enum",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    external_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    configuration: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    status: Mapped[SourceStatus] = mapped_column(
        Enum(
            SourceStatus,
            name="source_status_enum",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=SourceStatus.ACTIVE,
        nullable=False,
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )