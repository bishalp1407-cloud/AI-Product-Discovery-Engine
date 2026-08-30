from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()


engine = create_engine(
    settings.database_url,

    # Check pooled connections before handing them
    # to the application.
    pool_pre_ping=True,

    # Periodically recycle connections so long-lived
    # stale connections are less likely.
    pool_recycle=300,

    connect_args={
        # Limits establishing a new PostgreSQL connection.
        #
        # Do NOT put statement_timeout in "options" here.
        # Neon's pooled endpoint rejects that startup
        # parameter.
        "connect_timeout": 10,
    },
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()