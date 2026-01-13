"""Helpers for updating run progress and stats."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.run import Run


def _utc_timestamp() -> str:
    return f"{datetime.utcnow().isoformat()}Z"


def merge_run_stats(run: Run, updates: dict[str, Any]) -> None:
    """Merge updates into run.stats_json, preserving existing fields."""
    current = dict(run.stats_json) if isinstance(run.stats_json, dict) else {}
    current.update(updates)
    run.stats_json = current


def update_run_progress(
    run: Run,
    *,
    phase: str,
    total: int | None = None,
    completed: int | None = None,
    succeeded: int | None = None,
    failed: int | None = None,
    message: str | None = None,
    current_task: str | None = None,
) -> None:
    """Update progress fields for a run."""
    current = dict(run.stats_json) if isinstance(run.stats_json, dict) else {}
    progress: dict[str, Any] = {}
    existing_progress = current.get("progress")
    if isinstance(existing_progress, dict):
        progress.update(existing_progress)
    progress["phase"] = phase
    progress["updated_at"] = _utc_timestamp()
    if total is not None:
        progress["total"] = total
    if completed is not None:
        progress["completed"] = completed
    if succeeded is not None:
        progress["succeeded"] = succeeded
    if failed is not None:
        progress["failed"] = failed
    if message is not None:
        progress["message"] = message
    if current_task is not None:
        progress["current_task"] = current_task
    merge_run_stats(run, {"progress": progress})


def append_run_task(
    run: Run,
    *,
    task: str,
    stage: str | None = None,
    item_id: int | None = None,
    status: str | None = None,
    detail: str | None = None,
    limit: int = 200,
) -> None:
    """Append a task entry to run.stats_json.tasks."""
    current = dict(run.stats_json) if isinstance(run.stats_json, dict) else {}
    tasks = current.get("tasks")
    if not isinstance(tasks, list):
        tasks = []
    entry: dict[str, Any] = {
        "at": _utc_timestamp(),
        "task": task,
    }
    if stage is not None:
        entry["stage"] = stage
    if item_id is not None:
        entry["item_id"] = item_id
    if status is not None:
        entry["status"] = status
    if detail is not None:
        entry["detail"] = detail
    tasks.append(entry)
    if limit > 0 and len(tasks) > limit:
        tasks = tasks[-limit:]
    current["tasks"] = tasks
    run.stats_json = current
