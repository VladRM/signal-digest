# Signal Digest Backend Technical Notes

## Overview

The backend is a FastAPI service that stores content and run state in PostgreSQL
via SQLAlchemy. It exposes REST endpoints for managing topics/endpoints and for
running ingestion, AI processing, and brief generation. Long-running AI work is
executed in a background task with server-side timeouts and stale-run cleanup.

## Runtime Stack

- FastAPI for HTTP API.
- SQLAlchemy ORM with Alembic migrations.
- PostgreSQL (local via Docker Compose).
- LangGraph + Gemini (via LangChain) for AI processing.

## Configuration

Configuration is loaded from `backend/.env` using pydantic-settings.

Common variables:
- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `YOUTUBE_DATA_API_KEY`
- `TWITTER_API_KEY`
- `TAVILY_API_KEY`
- `TAVILY_SEARCH_DEPTH`
- `AI_RUN_TIMEOUT_SECONDS` (default 900)

## Data Model Highlights

- `Run` (`app/models/run.py`): tracks ingestion/AI/brief runs. Stores status,
  timestamps, and `stats_json` (JSONB) for metrics and progress updates.
- `AppSettings` (`app/models/app_settings.py`): persisted settings payload used
  by the UI and per-run orchestration.
- Content ingestion models: `ContentItem`, `Endpoint`, `ConnectorQuery`,
  `Topic`, `TopicAssignment`, `AIExtraction`, `Brief`, `BriefItem`.

## Runs and Progress Tracking

Runs are created with `status=running` and updated on completion or failure.
Progress is stored in `Run.stats_json.progress` and surfaced by the runs API.

Progress schema (example):
```json
{
  "progress": {
    "phase": "ai_processing",
    "total": 120,
    "completed": 40,
    "succeeded": 38,
    "failed": 2,
    "message": "Processed 40 of 120 items",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

Progress updates are emitted by:
- `AIOrchestrator` (per batch, `app/services/ai/orchestrator.py`)
- `IngestionOrchestrator` (per endpoint + Tavily step, `app/services/ingestion/orchestrator.py`)

## Ingestion Pipeline

`IngestionOrchestrator`:
- Loads enabled endpoints and runs an ingester per connector type (RSS, YouTube, X).
- Optionally runs Tavily topic ingestion when configured or enabled.
- Aggregates stats into `Run.stats_json` and records errors in `Run.error_text`.

Tavily ingestion:
- Runs per topic, normalizes results, deduplicates content items, and adds topic
  assignments (`app/services/ingestion/tavily.py`).

## AI Processing

`AIOrchestrator`:
- Queries unprocessed content items (no `AIExtraction`).
- Executes a LangGraph flow: classify → extract.
- Updates progress per batch and persists summary stats in `stats_json`.

AI runs are launched asynchronously in `run_ai_in_background` with a configurable
timeout (`AI_RUN_TIMEOUT_SECONDS` or per-run override). Timeout or exceptions
mark the run as `failed`.

Stale AI runs are marked failed at startup (`app/main.py`).

## Brief Builder

`BriefBuilder` creates a deterministic brief:
- Scores items based on topic priority, novelty, and recency.
- Applies caps (items per topic / total items).
- Creates a `Brief` record and `BriefItem` entries.
- Records options and metrics in `Run.stats_json`.

## API Surface (Summary)

Routers live in `app/routers`:
- `/api/topics` for topic CRUD
- `/api/endpoints` for endpoint CRUD
- `/api/run` to trigger runs and list history
- `/api/run/{id}/cancel` to cancel a running AI run
- `/api/brief` to retrieve briefs
- `/api/explore` to query content by filters
- `/api/settings` to read/update persisted defaults

## Migrations

Use Alembic:
```bash
poetry run alembic upgrade head
```

The settings table is stored in `app_settings` and runs table in `runs`.
