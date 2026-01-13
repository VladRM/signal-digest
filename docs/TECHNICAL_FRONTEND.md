# Signal Digest Frontend Technical Notes

## Overview

The frontend is a Next.js (App Router) app. It renders management pages for
topics, endpoints, runs, and settings, and it polls the backend for run status
updates. All data access goes through a typed API client.

## Runtime Stack

- Next.js + React (App Router)
- Tailwind CSS + shadcn/ui components
- Sonner for toast notifications

## Configuration

Backend API base URL:
- `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api`)

## API Client

`frontend/lib/api.ts` provides a typed wrapper around the backend endpoints.
It throws `ApiError` when the backend returns a non-2xx response.

Client groups:
- `topicsApi`, `endpointsApi`
- `runsApi` (ingestion, AI, brief trigger + list)
- `settingsApi` (GET/PUT)
- `briefsApi`, `exploreApi`

## Settings and Persistence

Settings live in two places:
- The backend (`/api/settings`), persisted to the database.
- Local storage for instant UI defaults (`frontend/lib/settings.ts`).

`/settings` page flow:
- Fetches settings from the backend, normalizes, and caches to local storage.
- Writes updates back to `/api/settings` using a short debounce.
- Defaults come from `DEFAULT_SETTINGS` in `frontend/lib/settings.ts`.

Local storage key: `sigdig.settings`.

## Runs and Progress UI

`/runs` page:
- Calls `runsApi.list()` on load.
- Polls every 5 seconds while any run is `running`.
- Renders a “Current Run” card with a progress bar and counts.
- Reads progress from `Run.stats_json.progress` (phase, total, completed, etc.).
- Allows cancelling a running AI run via `/api/run/{id}/cancel`.

Trigger buttons:
- Ingest: uses per-run settings (caps + Tavily options).
- AI: uses per-run timeout from settings.
- Brief: uses per-run caps/lookback options.

## Pages

App Router pages (`frontend/app`):
- `/topics`: CRUD for topics.
- `/endpoints`: CRUD for endpoints.
- `/runs`: run history + triggers + progress display.
- `/settings`: persisted runtime defaults.
- `/brief`: brief viewing.
- `/explore`: content browsing by filters.

Shared layout and navigation live in:
- `frontend/app/layout.tsx`
- `frontend/components/nav.tsx`

## Types

Shared TypeScript types live in `frontend/types/index.ts` and mirror backend
schemas for runs, settings, topics, and endpoints.
