from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.sync_job import SyncJob
from app.services.project_sync_service import sync_project


class SyncJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def create_sync_job(
    *,
    project_id: UUID,
) -> SyncJob:
    """
    Create and persist a new sync job.

    Job state lives in PostgreSQL rather than process memory,
    so API instances can retrieve the same job after a restart
    or deployment.
    """
    db = SessionLocal()

    try:
        job = SyncJob(
            project_id=project_id,
            status=SyncJobStatus.QUEUED.value,
            created_at=datetime.now(timezone.utc),
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        # Detach the object before closing the session so callers
        # can safely read its attributes.
        db.expunge(job)

        return job

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_sync_job(
    job_id: UUID,
) -> SyncJob | None:
    """
    Retrieve a persisted sync job from PostgreSQL.
    """
    db = SessionLocal()

    try:
        job = db.scalar(
            select(SyncJob).where(
                SyncJob.id == job_id,
            )
        )

        if job is None:
            return None

        db.expunge(job)

        return job

    finally:
        db.close()


def run_sync_job(
    *,
    job_id: UUID,
) -> None:
    """
    Execute a project sync and persist job state.

    The job record survives API process restarts because its
    lifecycle is stored in PostgreSQL.
    """

    # ---------------------------------------------------------
    # Mark job as running
    # ---------------------------------------------------------

    db = SessionLocal()

    try:
        job = db.get(SyncJob, job_id)

        if job is None:
            return

        job.status = SyncJobStatus.RUNNING.value
        job.started_at = datetime.now(timezone.utc)
        job.error = None

        project_id = job.project_id

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    # ---------------------------------------------------------
    # Run the actual sync in its own database session
    # ---------------------------------------------------------

    sync_db = SessionLocal()

    try:
        result = sync_project(
            sync_db,
            project_id=project_id,
        )

        if result is None:
            raise ValueError("Project not found.")

        # Convert nested dataclasses into JSON-compatible data.
        result_data = asdict(result)

        # UUID objects are not JSON serializable, so convert them
        # explicitly before writing the JSONB payload.
        result_data["project_id"] = str(result.project_id)

        for source in result_data.get("sources", []):
            source["source_id"] = str(source["source_id"])

        # -----------------------------------------------------
        # Persist successful completion
        # -----------------------------------------------------

        status_db = SessionLocal()

        try:
            job = status_db.get(SyncJob, job_id)

            if job is None:
                return

            job.result = result_data
            job.status = SyncJobStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            job.error = None

            status_db.commit()

        except Exception:
            status_db.rollback()
            raise

        finally:
            status_db.close()

    except Exception:
        sync_db.rollback()

        # -----------------------------------------------------
        # Persist failure
        # -----------------------------------------------------

        status_db = SessionLocal()

        try:
            job = status_db.get(SyncJob, job_id)

            if job is not None:
                job.status = SyncJobStatus.FAILED.value
                job.error = "Sync failed. Please try again."
                job.completed_at = datetime.now(timezone.utc)

                status_db.commit()

        except Exception:
            status_db.rollback()

        finally:
            status_db.close()

    finally:
        sync_db.close()