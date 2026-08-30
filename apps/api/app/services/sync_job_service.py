from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from uuid import UUID, uuid4

from app.db.session import SessionLocal
from app.services.project_sync_service import (
    ProjectSyncResult,
    sync_project,
)


class SyncJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncJob:
    id: UUID
    project_id: UUID
    status: SyncJobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: ProjectSyncResult | None = None


_jobs: dict[UUID, SyncJob] = {}
_jobs_lock = Lock()


def create_sync_job(
    *,
    project_id: UUID,
) -> SyncJob:
    job = SyncJob(
        id=uuid4(),
        project_id=project_id,
        status=SyncJobStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
    )

    with _jobs_lock:
        _jobs[job.id] = job

    return job


def get_sync_job(
    job_id: UUID,
) -> SyncJob | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def run_sync_job(
    *,
    job_id: UUID,
) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)

        if job is None:
            return

        job.status = SyncJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        project_id = job.project_id

    db = SessionLocal()

    try:
        result = sync_project(
            db,
            project_id=project_id,
        )

        if result is None:
            raise ValueError("Project not found.")

        with _jobs_lock:
            job = _jobs.get(job_id)

            if job is None:
                return

            job.result = result
            job.status = SyncJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)

    except Exception as exc:
        db.rollback()

        with _jobs_lock:
            job = _jobs.get(job_id)

            if job is not None:
                job.status = SyncJobStatus.FAILED
                job.error = str(exc)
                job.completed_at = datetime.now(timezone.utc)

    finally:
        db.close()