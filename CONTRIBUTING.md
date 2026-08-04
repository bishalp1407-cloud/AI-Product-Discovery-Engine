# Contributing

## Development setup

1. Clone the repository.
2. Create the backend virtual environment.
3. Install backend dependencies.
4. Install frontend dependencies.
5. Copy each `.env.example` file to the appropriate local environment file.
6. Run the backend and frontend development servers.

## Branch naming

Use descriptive branch names:

- `feature/project-management`
- `feature/feedback-ingestion`
- `fix/health-endpoint`
- `docs/database-architecture`

## Commit messages

Use clear commit messages:

- `feat: add project creation endpoint`
- `fix: handle invalid feedback payload`
- `docs: document monorepo architecture`
- `test: add health endpoint test`

## Code quality

Before opening a pull request:

### Backend

```powershell
python -m pytest
python -m ruff check .