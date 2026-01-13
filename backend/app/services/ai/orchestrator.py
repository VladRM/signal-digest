"""AI processing orchestrator using LangGraph."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from app.models.content_item import ContentItem
from app.models.endpoint import ConnectorType
from app.models.ai_extraction import AIExtraction
from app.models.run import Run, RunType, RunStatus
from app.services.ai.classifier import classify_node
from app.services.ai.extractor import extract_node
from app.services.ai.video_extractor import video_extract_node
from app.services.ai.constants import BATCH_SIZE, RATE_LIMIT_DELAY
from app.services.ai.task_utils import format_item_label
from app.services.run_progress import append_run_task, merge_run_stats, update_run_progress


class AIProcessingState(TypedDict, total=False):
    """State for AI processing workflow."""
    content_item: ContentItem
    db: Session
    is_video: bool
    classification_result: Optional[Dict[str, Any]]
    extraction_result: Optional[Dict[str, Any]]
    error: Optional[str]
    run: Run
    item_label: str
    classification_timeout_seconds: int
    extraction_timeout_seconds: int


def detect_content_type_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Determine if content is video or text.

    Args:
        state: Current state with content_item

    Returns:
        Updated state with is_video flag
    """
    content_item = state["content_item"]

    # Check if connector is YouTube
    is_video = content_item.connector_type == ConnectorType.YOUTUBE_CHANNEL

    return {
        **state,
        "is_video": is_video
    }


def route_by_content_type(state: Dict[str, Any]) -> str:
    """Route to video or text extraction based on content type.

    Args:
        state: Current state with is_video flag

    Returns:
        Next node name
    """
    return "video_extract" if state.get("is_video") else "text_extract"


class AIOrchestrator:
    """Orchestrate AI processing pipeline using LangGraph."""

    def __init__(self, db: Session):
        """Initialize the orchestrator.

        Args:
            db: Database session
        """
        self.db = db
        self.batch_size = BATCH_SIZE
        self.rate_limit_delay = RATE_LIMIT_DELAY
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Compiled graph
        """
        # Create workflow
        workflow = StateGraph(AIProcessingState)

        # Add nodes
        workflow.add_node("detect_type", detect_content_type_node)
        workflow.add_node("classify", classify_node)
        workflow.add_node("video_extract", video_extract_node)
        workflow.add_node("text_extract", extract_node)

        # Define edges
        workflow.set_entry_point("detect_type")
        workflow.add_edge("detect_type", "classify")
        workflow.add_conditional_edges(
            "classify",
            route_by_content_type,
            {
                "video_extract": "video_extract",
                "text_extract": "text_extract"
            }
        )
        workflow.add_edge("video_extract", END)
        workflow.add_edge("text_extract", END)

        # Compile graph
        return workflow.compile()

    async def run_pipeline(self, run: Run | None = None) -> Run:
        """Run AI processing on unprocessed content items.

        Returns:
            Run record with statistics
        """
        if run is None:
            run = Run(
                run_type=RunType.AI,
                started_at=datetime.utcnow(),
                status=RunStatus.RUNNING,
            )
            self.db.add(run)
            self.db.commit()
        else:
            updated = False
            if run.status != RunStatus.RUNNING:
                run.status = RunStatus.RUNNING
                updated = True
            if run.started_at is None:
                run.started_at = datetime.utcnow()
                updated = True
            if updated:
                self.db.commit()

        try:
            classification_timeout, extraction_timeout = self._resolve_ai_timeouts()

            # Get unprocessed items (no AI extraction)
            unprocessed_items = self._get_unprocessed_items()
            total_items = len(unprocessed_items)
            update_run_progress(
                run,
                phase="ai_processing",
                total=total_items,
                completed=0,
                succeeded=0,
                failed=0,
                message=f"Queued {total_items} items",
                current_task="Preparing items",
            )
            merge_run_stats(run, {
                "ai_timeouts": {
                    "classification_seconds": classification_timeout,
                    "extraction_seconds": extraction_timeout,
                }
            })
            append_run_task(
                run,
                task=f"Queued {total_items} items for AI processing",
                stage="queue",
                status="completed",
            )
            self.db.commit()

            if not unprocessed_items:
                update_run_progress(
                    run,
                    phase="ai_processing",
                    total=0,
                    completed=0,
                    succeeded=0,
                    failed=0,
                    message="No unprocessed items found",
                    current_task="No unprocessed items found",
                )
                append_run_task(
                    run,
                    task="No unprocessed items found",
                    stage="queue",
                    status="completed",
                )
                run.finished_at = datetime.utcnow()
                run.status = RunStatus.SUCCESS
                merge_run_stats(run, {
                    "items_processed": 0,
                    "items_succeeded": 0,
                    "items_failed": 0,
                    "message": "No unprocessed items found"
                })
                self.db.commit()
                return run

            # Process in batches, but update progress per item for visibility.
            total_processed = 0
            total_succeeded = 0
            total_failed = 0
            errors = []

            for i in range(0, len(unprocessed_items), self.batch_size):
                batch = unprocessed_items[i:i + self.batch_size]

                for item in batch:
                    item_label = format_item_label(item)
                    append_run_task(
                        run,
                        task=f"Starting item {item.id}",
                        stage="item",
                        item_id=item.id,
                        status="started",
                        detail=item_label,
                    )
                    update_run_progress(
                        run,
                        phase="ai_processing",
                        current_task=f"Starting item {item.id} ({item_label})",
                    )
                    self.db.commit()

                    result = await self._process_item(
                        item,
                        run,
                        item_label,
                        classification_timeout,
                        extraction_timeout,
                    )
                    total_processed += 1
                    if result.get("success"):
                        total_succeeded += 1
                    else:
                        total_failed += 1
                    if result.get("error"):
                        errors.append(result["error"])

                    append_run_task(
                        run,
                        task=f"Finished item {item.id}",
                        stage="item",
                        item_id=item.id,
                        status="completed" if result.get("success") else "failed",
                        detail=item_label if result.get("success") else result.get("error") or item_label,
                    )
                    update_run_progress(
                        run,
                        phase="ai_processing",
                        total=total_items,
                        completed=total_processed,
                        succeeded=total_succeeded,
                        failed=total_failed,
                        message=f"Processed {total_processed} of {total_items} items",
                        current_task=f"Processed item {item.id} ({item_label})",
                    )
                    self.db.commit()

                    # Rate limiting between items
                    await asyncio.sleep(self.rate_limit_delay)

            # Update run
            update_run_progress(
                run,
                phase="ai_processing",
                total=total_items,
                completed=total_processed,
                succeeded=total_succeeded,
                failed=total_failed,
                message="AI processing completed",
                current_task="AI processing completed",
            )
            append_run_task(
                run,
                task="AI processing completed",
                stage="complete",
                status="completed",
            )
            run.finished_at = datetime.utcnow()
            run.status = RunStatus.SUCCESS if total_failed == 0 else RunStatus.FAILED
            merge_run_stats(run, {
                "items_processed": total_processed,
                "items_succeeded": total_succeeded,
                "items_failed": total_failed,
                "errors": errors[:10]  # Limit errors in stats
            })
            self.db.commit()

            return run

        except Exception as e:
            run.finished_at = datetime.utcnow()
            run.status = RunStatus.FAILED
            run.error_text = str(e)
            self.db.commit()
            raise

    async def _process_item(
        self,
        item: ContentItem,
        run: Run,
        item_label: str,
        classification_timeout: int,
        extraction_timeout: int,
    ) -> Dict[str, Any]:
        """Process a single content item through the graph."""
        try:
            result = await self.graph.ainvoke(
                {
                    "content_item": item,
                    "db": self.db,
                    "is_video": False,
                    "classification_result": None,
                    "extraction_result": None,
                    "error": None,
                    "run": run,
                    "item_label": item_label,
                    "classification_timeout_seconds": classification_timeout,
                    "extraction_timeout_seconds": extraction_timeout,
                }
            )

            classification_success = (result.get("classification_result") or {}).get(
                "success", False
            )
            extraction_success = (result.get("extraction_result") or {}).get(
                "success", False
            )

            return {
                "success": classification_success and extraction_success,
                "item_id": item.id,
                "classification": result.get("classification_result"),
                "extraction": result.get("extraction_result"),
                "error": result.get("error"),
            }

        except Exception as e:
            error_msg = f"Failed to process item {item.id}: {str(e)}"
            return {
                "success": False,
                "item_id": item.id,
                "error": error_msg,
            }

    def _resolve_ai_timeouts(self) -> tuple[int, int]:
        from app.models.app_settings import AppSettings as AppSettingsModel
        from app.schemas.settings import AppSettings

        record = self.db.query(AppSettingsModel).first()
        if record:
            try:
                settings_payload = AppSettings.model_validate(record.settings_json or {})
            except Exception:
                settings_payload = AppSettings()
        else:
            settings_payload = AppSettings()

        classification_timeout = settings_payload.ai.classification_timeout_seconds
        extraction_timeout = settings_payload.ai.extraction_timeout_seconds
        return classification_timeout, extraction_timeout

    def _get_unprocessed_items(self) -> List[ContentItem]:
        """Get content items without AI extractions.

        Returns:
            List of unprocessed ContentItem objects
        """
        # Query items that don't have an AI extraction
        subquery = self.db.query(AIExtraction.content_item_id).distinct()

        unprocessed = self.db.query(ContentItem).filter(
            ~ContentItem.id.in_(subquery)
        ).order_by(ContentItem.published_at.desc()).all()

        return unprocessed


async def run_ai_processing(db: Session, run_id: int | None = None) -> Run:
    """Run AI processing pipeline.

    Args:
        db: Database session
        run_id: Existing run ID to update instead of creating a new one

    Returns:
        Run record
    """
    orchestrator = AIOrchestrator(db)
    if run_id is None:
        return await orchestrator.run_pipeline()
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise ValueError(f"Run {run_id} not found")
    return await orchestrator.run_pipeline(run)
