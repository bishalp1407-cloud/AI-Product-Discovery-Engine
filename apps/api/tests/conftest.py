import pytest
from sqlalchemy.orm import Session

from app.db.session import engine


def pytest_sessionstart(session):
    """
    Safety guard: never allow the test suite to run against
    a known hosted/production PostgreSQL database.
    """
    database_url = str(engine.url).lower()

    forbidden_hosts = (
        "neon.tech",
        "railway.app",
        "rlwy.net",
    )

    if any(host in database_url for host in forbidden_hosts):
        raise RuntimeError(
            "Refusing to run tests against a hosted database. "
            "Use a local/test DATABASE_URL."
        )


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()