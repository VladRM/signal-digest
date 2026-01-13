"""Brief builder service for creating daily briefs."""

from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload
from collections import defaultdict

from app.models.content_item import ContentItem
from app.models.topic_assignment import TopicAssignment
from app.models.ai_extraction import AIExtraction
from app.models.topic import Topic
from app.models.endpoint import Endpoint
from app.models.brief import Brief, BriefMode
from app.models.brief_item import BriefItem
from app.models.run import Run, RunType, RunStatus
from app.models.topic_brief import TopicBrief
from app.models.app_settings import AppSettings as AppSettingsModel
from app.schemas.run import RunBriefOptions
from app.schemas.settings import AppSettings as AppSettingsSchema
from app.services.ai.topic_brief_generator import TopicBriefGenerator
from app.services.run_progress import append_run_task, merge_run_stats, update_run_progress


class BriefBuilder:
    """Build daily briefs using deterministic ranking algorithm."""

    def __init__(self, db: Session):
        """Initialize the brief builder.

        Args:
            db: Database session
        """
        self.db = db
        self.max_items = 15
        self.max_per_topic = 3
        self.lookback_hours = 48

    def _load_app_settings(self) -> AppSettingsSchema:
        record = self.db.query(AppSettingsModel).first()
        if record:
            try:
                return AppSettingsSchema.model_validate(record.settings_json or {})
            except Exception:
                return AppSettingsSchema()
        return AppSettingsSchema()

    def _apply_app_settings(self) -> None:
        settings = self._load_app_settings()
        self.max_items = self._resolve_int(settings.brief.max_items, self.max_items, minimum=0)
        self.max_per_topic = self._resolve_int(
            settings.brief.max_per_topic, self.max_per_topic, minimum=0
        )
        self.lookback_hours = self._resolve_int(
            settings.brief.lookback_hours, self.lookback_hours, minimum=1
        )

    async def build_brief(
        self,
        target_date: Optional[str] = None,
        mode: str = "morning",
        options: Optional[RunBriefOptions] = None,
    ) -> Run:
        """Build brief for specified date.

        Args:
            target_date: Date string in YYYY-MM-DD format (default: today)
            mode: Brief mode (default: "morning")

        Returns:
            Run record with statistics
        """
        # Create run record
        run = Run(
            run_type=RunType.BUILD_BRIEF,
            started_at=datetime.utcnow(),
            status=RunStatus.RUNNING
        )
        self.db.add(run)
        self.db.commit()

        try:
            self._raise_if_cancelled(run)
            self._apply_app_settings()

            brief_steps_total = 4
            brief_steps_completed = 0

            update_run_progress(
                run,
                phase="brief_build",
                message="Starting brief build",
                current_task="Starting brief build",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            append_run_task(
                run,
                task="Starting brief build",
                stage="brief_build",
                status="started",
            )
            self.db.commit()

            if options:
                self._apply_options(options)
                append_run_task(
                    run,
                    task="Applied brief options",
                    stage="brief_build",
                    status="completed",
                )
                self.db.commit()

            update_run_progress(
                run,
                phase="brief_build",
                message="Finding candidate items",
                current_task="Finding candidate items",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            append_run_task(
                run,
                task="Finding candidate items",
                stage="brief_build",
                status="started",
            )
            self.db.commit()
            self._raise_if_cancelled(run)

            # Parse date
            brief_date = self._parse_date(target_date)

            # Get candidate items
            candidates = self._get_candidates(brief_date)
            self._raise_if_cancelled(run)
            brief_steps_completed = 1
            append_run_task(
                run,
                task="Candidate items loaded",
                stage="brief_build",
                status="completed",
                detail=f"{len(candidates)} candidates",
            )
            update_run_progress(
                run,
                phase="brief_build",
                message=f"Found {len(candidates)} candidates",
                current_task="Ranking candidate items",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            self.db.commit()

            if not candidates:
                options_payload = self._options_payload(options)
                update_run_progress(
                    run,
                    phase="brief_build",
                    total=0,
                    completed=0,
                    message="No candidate items found",
                    current_task="No candidate items found",
                )
                append_run_task(
                    run,
                    task="No candidate items found",
                    stage="brief_build",
                    status="completed",
                )
                run.finished_at = datetime.utcnow()
                run.status = RunStatus.SUCCESS
                merge_run_stats(run, {
                    "date": brief_date.isoformat(),
                    "mode": mode,
                    "candidates_evaluated": 0,
                    "items_selected": 0,
                    "message": "No candidate items found",
                    "options": options_payload,
                })
                self.db.commit()
                return run

            update_run_progress(
                run,
                phase="brief_build",
                message=f"Found {len(candidates)} candidates",
                current_task="Ranking candidate items",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            append_run_task(
                run,
                task="Ranking candidate items",
                stage="brief_build",
                status="started",
            )
            self.db.commit()
            self._raise_if_cancelled(run)

            # Rank items
            ranked_items = self._rank_items(candidates)
            self._raise_if_cancelled(run)
            brief_steps_completed = 2
            append_run_task(
                run,
                task="Ranked candidate items",
                stage="brief_build",
                status="completed",
                detail=f"{len(ranked_items)} ranked",
            )
            update_run_progress(
                run,
                phase="brief_build",
                message="Applying selection caps",
                current_task="Applying selection caps",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            self.db.commit()

            # Apply caps
            update_run_progress(
                run,
                phase="brief_build",
                message="Applying selection caps",
                current_task="Applying selection caps",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            append_run_task(
                run,
                task="Applying selection caps",
                stage="brief_build",
                status="started",
            )
            selected_items = self._apply_caps(ranked_items)
            self._raise_if_cancelled(run)
            brief_steps_completed = 3
            append_run_task(
                run,
                task="Selection caps applied",
                stage="brief_build",
                status="completed",
                detail=f"{len(selected_items)} selected",
            )
            update_run_progress(
                run,
                phase="brief_build",
                message="Creating brief",
                current_task="Creating brief",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            self.db.commit()

            # Create brief
            update_run_progress(
                run,
                phase="brief_build",
                message="Creating brief",
                current_task="Creating brief",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            append_run_task(
                run,
                task="Creating brief",
                stage="brief_build",
                status="started",
            )
            brief = self._create_brief(brief_date, mode, selected_items)
            self._raise_if_cancelled(run)
            brief_steps_completed = 4
            append_run_task(
                run,
                task="Brief created",
                stage="brief_build",
                status="completed",
                detail=f"{len(selected_items)} items",
            )
            update_run_progress(
                run,
                phase="brief_build",
                message=f"Selected {len(selected_items)} items",
                current_task="Generating topic briefs",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            self.db.commit()

            update_run_progress(
                run,
                phase="brief_build",
                message=f"Selected {len(selected_items)} items",
                current_task="Generating topic briefs",
                total=brief_steps_total,
                completed=brief_steps_completed,
            )
            append_run_task(
                run,
                task="Generating topic briefs",
                stage="topic_briefs",
                status="started",
            )
            self.db.commit()
            self._raise_if_cancelled(run)

            # Generate topic briefs
            topic_briefs_result = await self._generate_topic_briefs(
                brief=brief,
                brief_date=brief_date,
                candidates=candidates,  # ALL candidates, not just selected
                run=run,
            )
            self._raise_if_cancelled(run)

            # Update run
            run.finished_at = datetime.utcnow()
            run.status = RunStatus.SUCCESS
            merge_run_stats(run, {
                "date": brief_date.isoformat(),
                "mode": mode,
                "candidates_evaluated": len(candidates),
                "items_selected": len(selected_items),
                "brief_id": brief.id,
                "options": self._options_payload(options),
                "topic_briefs": {
                    "total_topics": topic_briefs_result["total"],
                    "generated": topic_briefs_result["count"],
                    "failed": len(topic_briefs_result["errors"]),
                    "errors": topic_briefs_result["errors"][:5]
                }
            })
            append_run_task(
                run,
                task="Brief build completed",
                stage="brief_build",
                status="completed",
            )
            self.db.commit()

            return run

        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            run.finished_at = datetime.utcnow()
            run.status = RunStatus.FAILED
            run.error_text = str(e)
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
            raise

    def _get_candidates(self, brief_date: date) -> List[ContentItem]:
        """Get content items eligible for brief.

        Args:
            brief_date: Date of the brief

        Returns:
            List of candidate ContentItem objects
        """
        # Items from last 48 hours before brief date
        cutoff = datetime.combine(brief_date, datetime.min.time()) - timedelta(
            hours=self.lookback_hours
        )

        # Must have:
        # - AI extraction
        # - At least one topic assignment
        # - From enabled endpoint (if any)
        # - Topic is enabled

        query = self.db.query(ContentItem).join(
            AIExtraction, ContentItem.id == AIExtraction.content_item_id
        ).join(
            TopicAssignment, ContentItem.id == TopicAssignment.content_item_id
        ).join(
            Topic, TopicAssignment.topic_id == Topic.id
        ).outerjoin(
            Endpoint, ContentItem.endpoint_id == Endpoint.id
        ).filter(
            and_(
                ContentItem.published_at >= cutoff,
                Topic.enabled == True,
                or_(ContentItem.endpoint_id.is_(None), Endpoint.enabled == True),
            )
        ).options(
            joinedload(ContentItem.topic_assignments).joinedload(TopicAssignment.topic),
            joinedload(ContentItem.ai_extractions),
            joinedload(ContentItem.endpoint)
        ).distinct().all()

        return query

    def _rank_items(self, candidates: List[ContentItem]) -> List[Tuple[float, ContentItem, TopicAssignment, AIExtraction]]:
        """Rank items by score.

        Args:
            candidates: List of ContentItem objects

        Returns:
            List of tuples (score, item, best_topic, extraction)
        """
        scored_items = []

        for item in candidates:
            # Get highest-scoring topic assignment
            if not item.topic_assignments:
                continue

            best_topic = max(item.topic_assignments, key=lambda ta: ta.score or 0)

            # Get latest extraction
            if not item.ai_extractions:
                continue

            extraction = item.ai_extractions[0]

            # Calculate score
            score = self._calculate_score(item, best_topic, extraction)

            scored_items.append((score, item, best_topic, extraction))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)

        return scored_items

    def _calculate_score(self, item: ContentItem, topic_assignment: TopicAssignment,
                        extraction: AIExtraction) -> float:
        """Calculate ranking score for an item.

        Args:
            item: ContentItem
            topic_assignment: TopicAssignment (best topic)
            extraction: AIExtraction

        Returns:
            Calculated score
        """
        score = 0.0

        # 1. Topic priority (0-100 scale, highest weight)
        topic_priority = (
            topic_assignment.topic.priority
            if topic_assignment.topic and topic_assignment.topic.priority is not None
            else 0
        )
        score += topic_priority * 10  # Weight: 10x

        # 2. Novelty score (0-10 scale)
        novelty_map = {
            "new": 10,
            "update": 5,
            "recurring": 2
        }
        extracted_json = (
            extraction.extracted_json
            if isinstance(extraction.extracted_json, dict)
            else {}
        )
        novelty = extracted_json.get("novelty", "recurring")
        score += novelty_map.get(novelty, 0)

        # 3. Recency score (0-10 scale)
        # More recent = higher score
        if item.published_at:
            hours_old = (datetime.utcnow() - item.published_at).total_seconds() / 3600
            recency_score = max(0, 48 - hours_old) / 4.8  # Max 10 points
            score += recency_score

        # 4. Endpoint weight (1-10 scale)
        endpoint_weight = 0
        if item.endpoint and item.endpoint.weight is not None:
            endpoint_weight = item.endpoint.weight
        score += endpoint_weight

        # 5. Confidence score (0-5 scale)
        confidence_map = {
            "high": 5,
            "med": 2,
            "low": 0
        }
        confidence = extracted_json.get("confidence_overall", "med")
        score += confidence_map.get(confidence, 0)

        # 6. Classification score (0-10 scale)
        # Use topic assignment score
        score += (topic_assignment.score or 0) * 10

        return score

    def _apply_caps(self, ranked_items: List[Tuple]) -> List[Tuple]:
        """Apply caps: max 15 total, max 3 per topic.

        Args:
            ranked_items: List of tuples (score, item, best_topic, extraction)

        Returns:
            Selected items after applying caps
        """
        selected = []
        topic_counts = {}

        for score, item, best_topic, extraction in ranked_items:
            topic_id = best_topic.topic_id

            # Check caps
            if len(selected) >= self.max_items:
                break

            if topic_counts.get(topic_id, 0) >= self.max_per_topic:
                continue

            # Add to selection
            selected.append((score, item, best_topic, extraction))
            topic_counts[topic_id] = topic_counts.get(topic_id, 0) + 1

        return selected

    def _apply_options(self, options: RunBriefOptions) -> None:
        """Apply per-run brief options to the builder."""
        max_items = self._resolve_int(options.max_items, self.max_items, minimum=0)
        max_per_topic = self._resolve_int(
            options.max_per_topic, self.max_per_topic, minimum=0
        )
        lookback_hours = self._resolve_int(
            options.lookback_hours, self.lookback_hours, minimum=1
        )
        self.max_items = max_items
        self.max_per_topic = max_per_topic
        self.lookback_hours = lookback_hours

    def _options_payload(self, options: Optional[RunBriefOptions]) -> Optional[dict]:
        """Build stats payload for brief options."""
        if not options:
            return None
        return {
            "max_items": self.max_items,
            "max_per_topic": self.max_per_topic,
            "lookback_hours": self.lookback_hours,
        }

    def _resolve_int(self, value: Optional[int], default: int, minimum: int) -> int:
        """Resolve integer options with fallback."""
        if value is None:
            return default
        try:
            resolved = int(value)
        except (TypeError, ValueError):
            return default
        return resolved if resolved >= minimum else default

    def _create_brief(self, brief_date: date, mode: str, items: List[Tuple]) -> Brief:
        """Create brief and brief_items records.

        Args:
            brief_date: Date of the brief
            mode: Brief mode
            items: Selected items

        Returns:
            Created Brief object
        """
        # Check if brief already exists
        existing = self.db.query(Brief).filter(
            and_(
                Brief.date == brief_date,
                Brief.mode == BriefMode.MORNING
            )
        ).first()

        if existing:
            # Delete old brief items and topic briefs
            self.db.query(BriefItem).filter(BriefItem.brief_id == existing.id).delete()
            self.db.query(TopicBrief).filter(TopicBrief.brief_id == existing.id).delete()
            brief = existing
        else:
            brief = Brief(
                date=brief_date,
                mode=BriefMode.MORNING
            )
            self.db.add(brief)
            self.db.flush()

        # Create brief items
        for rank, (score, item, best_topic, extraction) in enumerate(items, start=1):
            reason = self._generate_reason(score, best_topic, extraction)

            brief_item = BriefItem(
                brief_id=brief.id,
                content_item_id=item.id,
                rank=rank,
                reason_included=reason
            )
            self.db.add(brief_item)

        self.db.commit()
        return brief

    def _generate_reason(self, score: float, topic_assignment: TopicAssignment,
                        extraction: AIExtraction) -> str:
        """Generate human-readable reason for inclusion.

        Args:
            score: Calculated score
            topic_assignment: TopicAssignment
            extraction: AIExtraction

        Returns:
            Reason string
        """
        topic_name = topic_assignment.topic.name if topic_assignment.topic else "Unknown"
        extracted_json = (
            extraction.extracted_json
            if isinstance(extraction.extracted_json, dict)
            else {}
        )
        novelty = extracted_json.get("novelty", "")
        confidence = extracted_json.get("confidence_overall", "")

        return f"High-priority '{topic_name}' topic, {novelty} content with {confidence} confidence (score: {score:.1f})"

    def _parse_date(self, target_date: Optional[str] = None) -> date:
        """Parse date string or use today.

        Args:
            target_date: Date string in YYYY-MM-DD format

        Returns:
            Parsed date
        """
        if target_date:
            return datetime.strptime(target_date, "%Y-%m-%d").date()
        return date.today()

    async def _generate_topic_briefs(
        self,
        brief: Brief,
        brief_date: date,
        candidates: List[ContentItem],
        run: Run | None = None,
    ) -> Dict[str, Any]:
        """Generate AI briefs for each topic with content in lookback period.

        Args:
            brief: Created Brief object
            brief_date: Date of the brief
            candidates: ALL content items in lookback period

        Returns:
            Dict with generation statistics
        """
        # Load settings for timeout
        from app.models.app_settings import AppSettings as AppSettingsModel
        from app.schemas.settings import AppSettings

        settings_record = self.db.query(AppSettingsModel).first()
        if settings_record:
            try:
                settings = AppSettings.model_validate(settings_record.settings_json or {})
                timeout_seconds = settings.brief.topic_brief_timeout_seconds
            except Exception:
                timeout_seconds = 60  # Default
        else:
            timeout_seconds = 60  # Default

        # Group candidates by topic
        topic_content_map = self._group_candidates_by_topic(candidates)

        generator = TopicBriefGenerator(self.db)

        eligible_topics: list[tuple[Topic, List[ContentItem]]] = []
        for topic_id, content_items in topic_content_map.items():
            if len(content_items) < 2:
                continue
            topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                continue
            eligible_topics.append((topic, content_items))

        total_topics = len(eligible_topics)
        if run:
            self._raise_if_cancelled(run)
            update_run_progress(
                run,
                phase="topic_briefs",
                total=total_topics,
                completed=0,
                succeeded=0,
                failed=0,
                message=f"Queued {total_topics} topic briefs",
                current_task="Queued topic briefs",
            )
            append_run_task(
                run,
                task=f"Queued {total_topics} topic briefs",
                stage="topic_briefs",
                status="completed",
            )
            self.db.commit()

        results = []
        completed = 0
        succeeded = 0
        failed = 0

        for topic, content_items in eligible_topics:
            try:
                if run:
                    self._raise_if_cancelled(run)
                    update_run_progress(
                        run,
                        phase="topic_briefs",
                        current_task=f"Generating topic brief: {topic.name}",
                    )
                    append_run_task(
                        run,
                        task=f"Starting topic brief: {topic.name}",
                        stage="topic_briefs",
                        status="started",
                        detail=f"{len(content_items)} items",
                    )
                    self.db.commit()
                await generator.generate_for_topic(
                    topic=topic,
                    content_items=content_items,
                    brief_id=brief.id,
                    timeout_seconds=timeout_seconds
                )
                results.append({"success": True, "topic_id": topic.id})
                succeeded += 1
                if run:
                    append_run_task(
                        run,
                        task=f"Completed topic brief: {topic.name}",
                        stage="topic_briefs",
                        status="completed",
                        detail=f"{len(content_items)} items",
                    )
            except Exception as e:
                try:
                    self.db.rollback()
                except Exception:
                    pass
                error_msg = f"Topic {topic.name}: {str(e)}"
                results.append({
                    "success": False,
                    "topic_id": topic.id,
                    "error": error_msg
                })
                failed += 1
                if run:
                    append_run_task(
                        run,
                        task=f"Failed topic brief: {topic.name}",
                        stage="topic_briefs",
                        status="failed",
                        detail=error_msg,
                    )

            completed += 1
            if run:
                update_run_progress(
                    run,
                    phase="topic_briefs",
                    total=total_topics,
                    completed=completed,
                    succeeded=succeeded,
                    failed=failed,
                    message=f"Generated {completed} of {total_topics} topic briefs",
                    current_task=f"Finished topic brief: {topic.name}",
                )
                self.db.commit()

        if run:
            self._raise_if_cancelled(run)
            update_run_progress(
                run,
                phase="topic_briefs",
                total=total_topics,
                completed=completed,
                succeeded=succeeded,
                failed=failed,
                message="Topic briefs completed",
                current_task="Topic briefs completed",
            )
            append_run_task(
                run,
                task="Topic briefs completed",
                stage="topic_briefs",
                status="completed",
            )
            self.db.commit()

        return {
            "total": total_topics,
            "count": succeeded,
            "errors": [r["error"] for r in results if not r["success"]]
        }

    def _raise_if_cancelled(self, run: Run | None) -> None:
        """Abort the build if the run is cancelled."""
        if not run:
            return
        self.db.refresh(run)
        if run.status != RunStatus.RUNNING:
            raise RuntimeError("Brief run cancelled by user.")

    def _group_candidates_by_topic(
        self,
        candidates: List[ContentItem]
    ) -> Dict[int, List[ContentItem]]:
        """Group content items by their topics.

        Args:
            candidates: List of ContentItem objects

        Returns:
            Dict mapping topic_id to list of content items
        """
        topic_map = defaultdict(list)

        for item in candidates:
            for assignment in item.topic_assignments:
                topic_id = assignment.topic_id
                topic_map[topic_id].append(item)

        return dict(topic_map)
