# Signal Digest

A distraction-free daily brief system that aggregates content via connectors (RSS, YouTube, X/Twitter, Tavily), processes it through an AI pipeline, and delivers a finite Morning Brief.

## Stack

- **Frontend**: Next.js + React + shadcn/ui + Tailwind CSS
- **Backend**: Python FastAPI + PostgreSQL
- **AI**: LangChain + Gemini 3 Flash
- **Database**: PostgreSQL via Docker Compose

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (uses your default Python version)
- Poetry (for Python dependency management)
- Node.js 18+
- Google API Key (for Gemini)
- YouTube Data API Key
- Twitter API Key (twitterapi.io)
- Tavily API Key (tavily.com)

## Quick Start

### 1. Clone and Setup Environment

```bash
# Copy environment template
cp .env.example backend/.env

# Edit backend/.env and add your API keys:
# - GOOGLE_API_KEY
# - YOUTUBE_DATA_API_KEY
# - TWITTER_API_KEY
# - TAVILY_API_KEY
# - TAVILY_SEARCH_DEPTH (basic|advanced, optional)
# - AI_RUN_TIMEOUT_SECONDS (optional, default 900)
```

### 2. Start Database

```bash
# Start PostgreSQL and pgAdmin
docker compose up -d

# Access pgAdmin at http://localhost:5050
# Email: admin@local.dev
# Password: admin
```

### 3. Setup Backend

```bash
cd backend

# Install dependencies with Poetry (uses your default Python)
poetry install

# Activate Poetry shell
poetry shell

# Generate and run migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload
```

Backend will be available at http://localhost:8000

### 4. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Start Next.js dev server
npm run dev
```

Frontend will be available at http://localhost:3000

## Project Structure

```
sigdig/
├── docker-compose.yml       # PostgreSQL + pgAdmin
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── routers/        # API routes
│   │   └── services/       # Business logic
│   └── alembic/            # Database migrations
└── frontend/               # Next.js frontend
    └── src/
        ├── app/            # Next.js pages
        ├── components/     # React components
        └── lib/            # Utilities
```

## Key Features

- **Topics Management**: Configure topics with include/exclude rules and priorities
- **Endpoints Management**: Add RSS feeds, YouTube channels, and X accounts
- **Intelligent Ingestion**: Fetch and deduplicate content from all endpoints
- **AI Processing**: Topic classification and structured extraction via Gemini
- **Morning Brief**: Finite, curated list of 15 items with summaries
- **Topic Explorer**: Filter and explore content by topic and date
- **Settings & Defaults**: Configure ingestion, Tavily, AI timeout, and brief defaults in `/settings` (persisted to the database)
- **Run Monitoring**: Runs are async; `/runs` polls the API and surfaces progress updates during ingestion and AI processing

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

See [spec/plan_initial.md](spec/plan_initial.md) for the full implementation plan.

## License

MIT
