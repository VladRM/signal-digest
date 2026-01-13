# Signal Digest Backend

FastAPI backend for Signal Digest.

## Setup with Poetry

### Install Dependencies

```bash
cd backend

# Install dependencies with Poetry (uses your default Python version)
poetry install

# Activate the virtual environment
poetry shell
```

### Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys:
# - GOOGLE_API_KEY (from https://aistudio.google.com/app/apikey)
# - YOUTUBE_DATA_API_KEY (from https://console.cloud.google.com/apis/credentials)
# - TWITTER_API_KEY (from https://twitterapi.io)
# - TAVILY_API_KEY (from https://tavily.com)
# - TAVILY_SEARCH_DEPTH (basic|advanced, optional)
# - AI_RUN_TIMEOUT_SECONDS (optional, default 900)
```

### Database Migrations

```bash
# Generate initial migration
poetry run alembic revision --autogenerate -m "Initial schema"

# Apply migrations
poetry run alembic upgrade head
```

### Run Development Server

```bash
# Run with Poetry
poetry run uvicorn app.main:app --reload

# Or if you're in the Poetry shell
uvicorn app.main:app --reload
```

The API will be available at:
- http://localhost:8000 - API endpoint
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc documentation

## Settings API

Application settings are persisted in the database and exposed via:

- `GET /api/settings` to read current defaults
- `PUT /api/settings` to update defaults

Runs expose progress in `Run.stats_json.progress` while the run is `running`.

## Database Management

### Run PostgreSQL with Docker Compose

From the project root:

```bash
docker compose up -d
```

Access pgAdmin at http://localhost:5050 (admin@local.dev / admin)

### Create New Migration

```bash
poetry run alembic revision --autogenerate -m "Description of changes"
poetry run alembic upgrade head
```

### Rollback Migration

```bash
poetry run alembic downgrade -1
```

## Development

### Run Tests (once implemented)

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black .
poetry run ruff check .
```
