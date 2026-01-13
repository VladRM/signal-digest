"""FastAPI application entry point."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.ai.background import cleanup_stale_ai_runs

app = FastAPI(
    title="Signal Digest API",
    description="Backend API for Signal Digest - distraction-free daily brief system",
    version="0.1.0",
)

logger = logging.getLogger(__name__)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Signal Digest API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.on_event("startup")
def cleanup_stale_runs() -> None:
    """Cleanup stale AI runs on startup."""
    cleaned = cleanup_stale_ai_runs()
    if cleaned:
        logger.warning("Marked %s stale AI runs as failed on startup.", cleaned)

# Import and include routers
from app.routers import topics, endpoints, runs, briefs, explore, settings

app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(endpoints.router, prefix="/api/endpoints", tags=["endpoints"])
app.include_router(runs.router, prefix="/api/run", tags=["runs"])
app.include_router(briefs.router, prefix="/api", tags=["briefs"])
app.include_router(explore.router, prefix="/api", tags=["explore"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
