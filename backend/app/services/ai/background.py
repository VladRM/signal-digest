"""Background runner for AI processing."""
import asyncio
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.models.run import Run, RunStatus, RunType
from app.services.ai.orchestrator import run_ai_processing

logger = logging.getLogger(__name__)

_background_tasks: dict[int, asyncio.Task] = {}


def _append_error(existing: str | None, message: str) -> str:
    if existing:
        return f"{existing}\n\n{message}"
    return message


def _mark_run_failed(run_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run or run.status != RunStatus.RUNNING:
            return
        run.status = RunStatus.FAILED
        run.finished_at = datetime.utcnow()
        run.error_text = _append_error(run.error_text, message)
        db.commit()
    finally:
        db.close()


def cancel_ai_task(run_id: int) -> bool:
    """Cancel a running AI task if it is still active."""
    task = _background_tasks.get(run_id)
    if task is None or task.done():
        return False
    task.cancel()
    return True


def cleanup_stale_ai_runs() -> int:
    """Mark stale AI runs as failed on startup."""
    db = SessionLocal()
    try:
        runs = (
            db.query(Run)
            .filter(
                Run.run_type == RunType.AI,
                Run.status == RunStatus.RUNNING,
            )
            .all()
        )
        if not runs:
            return 0
        now = datetime.utcnow()
        total = 0
        for run in runs:
            timeout_seconds = settings.ai_run_timeout_seconds
            if isinstance(run.stats_json, dict):
                override = run.stats_json.get("timeout_seconds")
                if isinstance(override, (int, float)):
                    timeout_seconds = int(override)
            cutoff = now - timedelta(seconds=timeout_seconds)
            if run.started_at > cutoff:
                continue
            message = (
                f"AI run timed out after {timeout_seconds} seconds (startup cleanup)."
            )
            run.status = RunStatus.FAILED
            run.finished_at = now
            run.error_text = _append_error(run.error_text, message)
            total += 1
        db.commit()
        return total
    finally:
        db.close()


async def _execute_ai_run(run_id: int) -> None:
    db = SessionLocal()
    try:
        await run_ai_processing(db, run_id=run_id)
    finally:
        db.close()


async def run_ai_in_background(run_id: int, timeout_seconds: int | None = None) -> None:
    """Execute an AI run in the background with a timeout."""
    effective_timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else settings.ai_run_timeout_seconds
    )
    task = asyncio.create_task(_execute_ai_run(run_id))
    _background_tasks[run_id] = task
    task.add_done_callback(lambda _: _background_tasks.pop(run_id, None))

    try:
        await asyncio.wait_for(task, timeout=effective_timeout)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except Exception:
            pass
        _mark_run_failed(
            run_id,
            f"AI run timed out after {effective_timeout} seconds.",
        )
    except asyncio.CancelledError:
        # Task was cancelled explicitly (e.g., by user).
        return
    except Exception as exc:
        logger.exception("AI run failed (run_id=%s)", run_id)
        _mark_run_failed(run_id, f"AI run failed: {exc}")
