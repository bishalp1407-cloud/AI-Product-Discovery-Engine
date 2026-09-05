from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable
from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.sync_job import SyncJob
from app.services.project_sync_service import sync_project


STALE_JOB_TIMEOUT = timedelta(minutes=30)


class SyncJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def mark_stale_sync_jobs() -> int:
    """
    Mark long-running sync jobs as failed.

    This handles cases where the API process was stopped or restarted
    while a background sync was still running.
    """
    db = SessionLocal()

    try:
        cutoff = (
            datetime.now(timezone.utc)
            - STALE_JOB_TIMEOUT
        )

        stale_jobs = db.scalars(
            select(SyncJob).where(
                SyncJob.status
                == SyncJobStatus.RUNNING.value,
                SyncJob.started_at.is_not(None),
                SyncJob.started_at < cutoff,
            )
        ).all()

        for job in stale_jobs:
            job.status = SyncJobStatus.FAILED.value
            job.completed_at = datetime.now(
                timezone.utc
            )
            job.error = (
                "Sync interrupted before completion."
            )

        db.commit()

        return len(stale_jobs)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def create_sync_job(
    *,
    project_id: UUID,
) -> tuple[SyncJob, bool]:
    """
    Create and persist a sync job.

    Returns:
        (job, created)

    If the project already has a queued or running job,
    return that job instead of creating a duplicate.
    """
    mark_stale_sync_jobs()

    db = SessionLocal()

    try:
        existing_job = db.scalar(
            select(SyncJob)
            .where(
                SyncJob.project_id == project_id,
                SyncJob.status.in_(
                    [
                        SyncJobStatus.QUEUED.value,
                        SyncJobStatus.RUNNING.value,
                    ]
                ),
            )
            .order_by(
                SyncJob.created_at.desc()
            )
        )

        if existing_job is not None:
            db.expunge(existing_job)
            return existing_job, False

        job = SyncJob(
            project_id=project_id,
            status=SyncJobStatus.QUEUED.value,
            created_at=datetime.now(
                timezone.utc
            ),
        )

        db.add(job)
        db.commit()
        db.refresh(job)
        db.expunge(job)

        return job, True

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


def get_active_sync_job(
    *,
    project_id: UUID,
) -> SyncJob | None:
    """
    Return the newest queued or running sync job for a project.
    """
    mark_stale_sync_jobs()

    db = SessionLocal()

    try:
        job = db.scalar(
            select(SyncJob)
            .where(
                SyncJob.project_id == project_id,
                SyncJob.status.in_(
                    [
                        SyncJobStatus.QUEUED.value,
                        SyncJobStatus.RUNNING.value,
                    ]
                ),
            )
            .order_by(
                SyncJob.created_at.desc()
            )
        )

        if job is None:
            return None

        db.expunge(job)

        return job

    finally:
        db.close()


def _update_job_progress(
    *,
    job_id: UUID,
    current_stage: str | None = None,
    total_items: int | None = None,
    processed_items: int | None = None,
    total_batches: int | None = None,
    completed_batches: int | None = None,
) -> None:
    """
    Persist observable progress for a sync job.

    Only supplied fields are changed. This allows individual
    stages to update the fields they own without resetting
    progress from other stages.
    """
    db = SessionLocal()

    try:
        job = db.get(
            SyncJob,
            job_id,
        )

        if job is None:
            return

        if current_stage is not None:
            job.current_stage = current_stage

        if total_items is not None:
            job.total_items = total_items

        if processed_items is not None:
            job.processed_items = processed_items

        if total_batches is not None:
            job.total_batches = total_batches

        if completed_batches is not None:
            job.completed_batches = completed_batches

        db.commit()

    except Exception:
        db.rollback()
        raise

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
        job = db.get(
            SyncJob,
            job_id,
        )

        if job is None:
            return

        job.status = (
            SyncJobStatus.RUNNING.value
        )
        job.started_at = datetime.now(
            timezone.utc
        )
        job.error = None
        job.current_stage = "starting"
        job.total_items = 0
        job.processed_items = 0
        job.total_batches = 0
        job.completed_batches = 0

        project_id = job.project_id

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    # ---------------------------------------------------------
    # Progress callback
    # ---------------------------------------------------------

    def report_progress(
        *,
        current_stage: str | None = None,
        total_items: int | None = None,
        processed_items: int | None = None,
        total_batches: int | None = None,
        completed_batches: int | None = None,
    ) -> None:
        _update_job_progress(
            job_id=job_id,
            current_stage=current_stage,
            total_items=total_items,
            processed_items=processed_items,
            total_batches=total_batches,
            completed_batches=completed_batches,
        )

    # ---------------------------------------------------------
    # Run actual sync
    # ---------------------------------------------------------

    sync_db = SessionLocal()

    try:
        result = sync_project(
            sync_db,
            project_id=project_id,
            progress_callback=report_progress,
        )

        if result is None:
            raise ValueError(
                "Project not found."
            )

        result_data = asdict(result)

        result_data["project_id"] = str(
            result.project_id
        )

        for source in result_data.get(
            "sources",
            [],
        ):
            source["source_id"] = str(
                source["source_id"]
            )

        # -----------------------------------------------------
        # Persist successful completion
        # -----------------------------------------------------

        status_db = SessionLocal()

        try:
            job = status_db.get(
                SyncJob,
                job_id,
            )

            if job is None:
                return

            job.result = result_data
            job.status = (
                SyncJobStatus.COMPLETED.value
            )
            job.current_stage = "completed"
            job.completed_at = datetime.now(
                timezone.utc
            )
            job.error = None

            status_db.commit()

        except Exception:
            status_db.rollback()
            raise

        finally:
            status_db.close()

    except Exception as exc:
        sync_db.rollback()

        # -----------------------------------------------------
        # Persist failure
        # -----------------------------------------------------

        status_db = SessionLocal()

        try:
            job = status_db.get(
                SyncJob,
                job_id,
            )

            if job is not None:
                job.status = (
                    SyncJobStatus.FAILED.value
                )
                job.current_stage = "failed"
                job.error = str(exc)
                job.completed_at = datetime.now(
                    timezone.utc
                )

                status_db.commit()

        except Exception:
            status_db.rollback()

        finally:
            status_db.close()

    finally:
        sync_db.close()