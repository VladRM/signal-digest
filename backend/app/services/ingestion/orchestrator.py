"""Ingestion orchestrator."""
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.app_settings import AppSettings as AppSettingsModel
from app.models.endpoint import Endpoint, ConnectorType
from app.models.run import Run, RunType, RunStatus
from app.schemas.run import RunIngestionOptions, TavilyRunOptions
from app.schemas.settings import AppSettings as AppSettingsSchema
from app.services.ingestion.rss import RSSIngester
from app.services.ingestion.youtube import YouTubeIngester
from app.services.ingestion.twitter import TwitterIngester
from app.services.ingestion.tavily import TavilyTopicIngester
from app.services.run_progress import merge_run_stats, update_run_progress


class IngestionOrchestrator:
    """Orchestrate ingestion from all enabled endpoints."""

    def __init__(self, db: Session):
        self.db = db

    def _load_app_settings(self) -> AppSettingsSchema:
        record = self.db.query(AppSettingsModel).first()
        if record:
            try:
                return AppSettingsSchema.model_validate(record.settings_json or {})
            except Exception:
                return AppSettingsSchema()
        return AppSettingsSchema()

    def _resolve_tavily_time_range(self, time_range: str | None) -> str | None:
        if time_range is None:
            return None
        normalized = time_range.strip().lower()
        return None if normalized == "none" else time_range

    def _resolve_ingestion_options(
        self,
        options: RunIngestionOptions | None,
        app_settings: AppSettingsSchema,
    ) -> RunIngestionOptions:
        if options is None:
            options = RunIngestionOptions()
        tavily_options = options.tavily or TavilyRunOptions()
        return RunIngestionOptions(
            rss_max_items=(
                options.rss_max_items
                if options.rss_max_items is not None
                else app_settings.ingestion.rss_max_items
            ),
            youtube_max_items=(
                options.youtube_max_items
                if options.youtube_max_items is not None
                else app_settings.ingestion.youtube_max_items
            ),
            twitter_max_items=(
                options.twitter_max_items
                if options.twitter_max_items is not None
                else app_settings.ingestion.twitter_max_items
            ),
            tavily=TavilyRunOptions(
                enabled=tavily_options.enabled,
                search_depth=(
                    tavily_options.search_depth
                    if tavily_options.search_depth is not None
                    else app_settings.tavily.search_depth
                ),
                max_results=(
                    tavily_options.max_results
                    if tavily_options.max_results is not None
                    else app_settings.tavily.max_results
                ),
                topic=(
                    tavily_options.topic
                    if tavily_options.topic is not None
                    else app_settings.tavily.topic
                ),
                time_range=self._resolve_tavily_time_range(
                    tavily_options.time_range
                    if tavily_options.time_range is not None
                    else app_settings.tavily.time_range
                ),
                include_raw_content=(
                    tavily_options.include_raw_content
                    if tavily_options.include_raw_content is not None
                    else app_settings.tavily.include_raw_content
                ),
                include_answer=tavily_options.include_answer,
                start_date=tavily_options.start_date,
                end_date=tavily_options.end_date,
                fetch_window_hours=tavily_options.fetch_window_hours,
            ),
        )

    def get_ingester(self, endpoint: Endpoint, options: RunIngestionOptions | None):
        """Get appropriate ingester for connector type."""
        if endpoint.connector_type == ConnectorType.RSS:
            max_items = options.rss_max_items if options else None
            return RSSIngester(self.db, endpoint, max_items=max_items)
        elif endpoint.connector_type == ConnectorType.YOUTUBE_CHANNEL:
            max_items = options.youtube_max_items if options else None
            return YouTubeIngester(self.db, endpoint, max_items=max_items)
        elif endpoint.connector_type == ConnectorType.X_USER:
            max_items = options.twitter_max_items if options else None
            return TwitterIngester(self.db, endpoint, max_items=max_items)
        else:
            raise ValueError(f"Unknown connector type: {endpoint.connector_type}")

    async def run_ingestion(self, options: RunIngestionOptions | None = None) -> Run:
        """Run ingestion from all enabled endpoints."""
        app_settings = self._load_app_settings()
        options = self._resolve_ingestion_options(options, app_settings)

        # Create run record
        run = Run(
            run_type=RunType.INGEST,
            started_at=datetime.utcnow(),
            status=RunStatus.RUNNING,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        # Initialize stats
        total_stats = {
            "endpoints_processed": 0,
            "endpoints_failed": 0,
            "total_fetched": 0,
            "total_new": 0,
            "total_skipped": 0,
            "topics_processed": 0,
            "topics_failed": 0,
            "total_results": 0,
            "tavily_items_new": 0,
            "tavily_items_existing": 0,
            "tavily_items_skipped": 0,
            "tavily_assignments_created": 0,
            "errors": [],
            "endpoint_details": [],
            "topic_details": [],
        }

        try:
            tavily_options = options.tavily if options else None
            tavily_enabled = None if tavily_options is None else tavily_options.enabled
            if tavily_options:
                total_stats["tavily_options"] = tavily_options.model_dump()

            # Get all enabled endpoints
            endpoints = (
                self.db.query(Endpoint)
                .filter(
                    Endpoint.enabled == True,
                    Endpoint.connector_type != ConnectorType.TAVILY,
                )
                .all()
            )
            tavily_should_run = tavily_enabled is True or (
                tavily_enabled is None and settings.tavily_api_key
            )
            total_steps = len(endpoints) + (1 if tavily_should_run else 0)
            progress_completed = 0
            update_run_progress(
                run,
                phase="endpoints",
                total=total_steps,
                completed=progress_completed,
                message=f"{len(endpoints)} endpoints queued",
            )
            self.db.commit()

            print(f"[Ingestion] Starting ingestion for {len(endpoints)} enabled endpoints")

            # Process each endpoint
            for endpoint in endpoints:
                endpoint_result = {
                    "endpoint_id": endpoint.id,
                    "endpoint_name": endpoint.name,
                    "connector_type": endpoint.connector_type.value,
                    "status": "success",
                }

                try:
                    print(
                        f"[Ingestion] Processing {endpoint.connector_type.value}: {endpoint.name}"
                    )

                    # Get appropriate ingester
                    ingester = self.get_ingester(endpoint, options)

                    # Run ingestion
                    stats = await ingester.ingest()

                    # Update totals
                    total_stats["endpoints_processed"] += 1
                    total_stats["total_fetched"] += stats["items_fetched"]
                    total_stats["total_new"] += stats["items_new"]
                    total_stats["total_skipped"] += stats["items_skipped"]

                    # Add endpoint stats
                    endpoint_result.update(stats)

                    print(
                        f"[Ingestion] {endpoint.name}: "
                        f"fetched={stats['items_fetched']}, "
                        f"new={stats['items_new']}, "
                        f"skipped={stats['items_skipped']}"
                    )

                except Exception as e:
                    error_msg = f"Error processing {endpoint.name}: {str(e)}"
                    print(f"[Ingestion] {error_msg}")

                    total_stats["endpoints_failed"] += 1
                    total_stats["errors"].append(error_msg)

                    endpoint_result["status"] = "failed"
                    endpoint_result["error"] = str(e)

                total_stats["endpoint_details"].append(endpoint_result)
                progress_completed += 1
                update_run_progress(
                    run,
                    phase="endpoints",
                    total=total_steps,
                    completed=progress_completed,
                    message=f"Processed {endpoint.name}",
                )
                self.db.commit()

            if tavily_should_run:
                update_run_progress(
                    run,
                    phase="tavily",
                    total=total_steps,
                    completed=progress_completed,
                    message="Running Tavily search",
                )
                self.db.commit()
                tavily_failed = False
                try:
                    ingester = TavilyTopicIngester(
                        self.db,
                        options=tavily_options or TavilyRunOptions(),
                    )
                    tavily_stats = await ingester.ingest_topics()

                    total_stats["topics_processed"] += tavily_stats.get("topics_processed", 0)
                    total_stats["topics_failed"] += tavily_stats.get("topics_failed", 0)
                    total_stats["total_results"] += tavily_stats.get("total_results", 0)
                    total_stats["total_new"] += tavily_stats.get("items_new", 0)
                    total_stats["total_skipped"] += tavily_stats.get("items_skipped", 0)
                    total_stats["tavily_items_new"] += tavily_stats.get("items_new", 0)
                    total_stats["tavily_items_existing"] += tavily_stats.get("items_existing", 0)
                    total_stats["tavily_items_skipped"] += tavily_stats.get("items_skipped", 0)
                    total_stats["tavily_assignments_created"] += tavily_stats.get(
                        "assignments_created", 0
                    )
                    total_stats["errors"].extend(tavily_stats.get("errors", []))
                    total_stats["topic_details"].extend(tavily_stats.get("topic_details", []))
                    total_stats["tavily_options"] = tavily_stats.get("tavily_options")
                except Exception as e:
                    error_msg = f"Tavily ingestion failed: {str(e)}"
                    total_stats["topics_failed"] += 1
                    total_stats["errors"].append(error_msg)
                    tavily_failed = True
                progress_completed += 1
                update_run_progress(
                    run,
                    phase="tavily",
                    total=total_steps,
                    completed=progress_completed,
                    message="Tavily search failed" if tavily_failed else "Tavily search completed",
                )
                self.db.commit()

            if tavily_enabled is True and not settings.tavily_api_key:
                raise Exception("Tavily API key not configured")

            # Update run record
            run.finished_at = datetime.utcnow()
            run.status = (
                RunStatus.SUCCESS
                if total_stats["endpoints_failed"] == 0
                and total_stats["topics_failed"] == 0
                else RunStatus.FAILED
            )
            merge_run_stats(run, total_stats)

            if total_stats["errors"]:
                run.error_text = "\n".join(total_stats["errors"])

            self.db.commit()
            self.db.refresh(run)

            print(
                f"[Ingestion] Completed: "
                f"{total_stats['total_new']} new items from "
                f"{total_stats['endpoints_processed']} endpoints"
            )

        except Exception as e:
            error_msg = f"Critical error during ingestion: {str(e)}"
            print(f"[Ingestion] {error_msg}")

            run.finished_at = datetime.utcnow()
            run.status = RunStatus.FAILED
            run.error_text = error_msg
            merge_run_stats(run, total_stats)

            self.db.commit()
            self.db.refresh(run)

        return run
