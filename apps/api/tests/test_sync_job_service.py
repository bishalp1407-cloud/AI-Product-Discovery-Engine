from uuid import uuid4

from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.sync_job import SyncJob
from app.services.sync_job_service import (
    SyncJobStatus,
    create_sync_job,
    get_sync_job,
)


def test_sync_job_persists_across_database_sessions():
    project_id = uuid4()

    db = SessionLocal()

    try:
        project = Project(
            id=project_id,
            name="Sync Job Persistence Test",
        )

        db.add(project)
        db.commit()

        job = create_sync_job(
            project_id=project_id,
        )

        job_id = job.id

        assert job.status == SyncJobStatus.QUEUED.value

        # get_sync_job() creates an entirely separate SessionLocal
        # session. Successful retrieval proves the job is stored in
        # PostgreSQL rather than process-local memory.
        retrieved_job = get_sync_job(job_id)

        assert retrieved_job is not None
        assert retrieved_job.id == job_id
        assert retrieved_job.project_id == project_id
        assert retrieved_job.status == SyncJobStatus.QUEUED.value

    finally:
        cleanup_db = SessionLocal()

        try:
            cleanup_db.execute(
                delete(SyncJob).where(
                    SyncJob.project_id == project_id,
                )
            )

            cleanup_db.execute(
                delete(Project).where(
                    Project.id == project_id,
                )
            )

            cleanup_db.commit()

        finally:
            cleanup_db.close()

        db.close()