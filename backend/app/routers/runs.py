"""Runs API router."""
import asyncio
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.run import Run, RunStatus, RunType
from app.models.app_settings import AppSettings as AppSettingsModel
from app.schemas.run import Run as RunSchema, RunAiOptions, RunBriefOptions, RunIngestionOptions
from app.schemas.settings import AppSettings as AppSettingsSchema
from app.config import settings
from app.services.ingestion.orchestrator import IngestionOrchestrator
from app.services.ai.background import cancel_ai_task, run_ai_in_background
from app.services.brief_builder import BriefBuilder

router = APIRouter()


@router.post("/ingest", response_model=RunSchema)
async def run_ingestion(
    options: RunIngestionOptions | None = Body(default=None),
    db: Session = Depends(get_db)
):
    """Trigger ingestion from all enabled endpoints."""
    try:
        orchestrator = IngestionOrchestrator(db)
        run = await orchestrator.run_ingestion(options)
        return run
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


def _load_app_settings(db: Session) -> AppSettingsSchema:
    record = db.query(AppSettingsModel).first()
    if record:
        try:
            return AppSettingsSchema.model_validate(record.settings_json or {})
        except Exception:
            return AppSettingsSchema()
    return AppSettingsSchema()


def _coerce_positive_int(value: int | None) -> int | None:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return None
    return resolved if resolved > 0 else None


def _resolve_ai_timeout(
    options: RunAiOptions | None,
    default_timeout: int | None,
) -> int | None:
    default_value = _coerce_positive_int(default_timeout)
    if not options or options.timeout_seconds is None:
        return default_value
    override = _coerce_positive_int(options.timeout_seconds)
    return override if override is not None else default_value


@router.post("/ai", response_model=RunSchema)
async def run_ai(
    options: RunAiOptions | None = Body(default=None),
    db: Session = Depends(get_db),
):
    """Trigger AI processing on unprocessed content items."""
    try:
        app_settings = _load_app_settings(db)
        timeout_seconds = _resolve_ai_timeout(options, app_settings.ai.timeout_seconds)
        effective_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.ai_run_timeout_seconds
        )
        run = Run(
            run_type=RunType.AI,
            started_at=datetime.utcnow(),
            status=RunStatus.RUNNING,
            stats_json={"timeout_seconds": effective_timeout},
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        asyncio.create_task(run_ai_in_background(run.id, timeout_seconds=effective_timeout))
        return run
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


@router.post("/build-brief", response_model=RunSchema)
async def build_brief(
    date: str = Query(default=None, description="YYYY-MM-DD format"),
    mode: str = Query(default="morning"),
    options: RunBriefOptions | None = Body(default=None),
    db: Session = Depends(get_db),
):
    """Build daily brief for specified date."""
    try:
        builder = BriefBuilder(db)
        run = await builder.build_brief(date, mode, options)
        return run
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brief building failed: {str(e)}")



@router.get("", response_model=list[RunSchema])
def list_runs(limit: int = 50, db: Session = Depends(get_db)):
    """List recent runs."""
    runs = db.query(Run).order_by(Run.started_at.desc()).limit(limit).all()
    return runs


@router.get("/{run_id}", response_model=RunSchema)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get a specific run by ID."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def _append_error(existing: str | None, message: str) -> str:
    if existing:
        return f"{existing}\n\n{message}"
    return message


@router.post("/{run_id}/cancel", response_model=RunSchema)
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    """Cancel a running AI run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.RUNNING:
        return run
    if run.run_type not in {RunType.AI, RunType.BUILD_BRIEF}:
        raise HTTPException(
            status_code=400,
            detail="Only AI and brief runs can be cancelled.",
        )

    run.status = RunStatus.FAILED
    run.finished_at = datetime.utcnow()
    cancel_message = (
        "AI run cancelled by user."
        if run.run_type == RunType.AI
        else "Brief run cancelled by user."
    )
    run.error_text = _append_error(run.error_text, cancel_message)
    db.commit()
    db.refresh(run)

    if run.run_type == RunType.AI:
        cancel_ai_task(run_id)
    return run
