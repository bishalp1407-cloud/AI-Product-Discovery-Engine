from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.models.project import Project
from app.models.feedback_source import FeedbackSource
from app.models.feedback import Feedback
from app.models.feedback_analysis import FeedbackAnalysis
from app.models.insight import Insight
from app.models.insight_feedback import InsightFeedback
from app.models.sync_job import SyncJob

# Alembic Config object
config = context.config

# Load DATABASE_URL from .env through our settings layer
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic uses this metadata to detect model/schema changes
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a live DB connection."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()