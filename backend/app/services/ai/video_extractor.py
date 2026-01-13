"""Video extraction service using Gemini's video understanding capabilities."""

from typing import Dict, Any
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from google.api_core.exceptions import DeadlineExceeded
from datetime import datetime
import asyncio

from app.models.content_item import ContentItem
from app.models.ai_extraction import AIExtraction
from app.services.ai.base import BaseAIService
from app.services.ai.prompts import PromptRegistry
from app.services.ai.extractor import ExtractionOutput
from app.config import settings
from app.services.run_progress import append_run_task, update_run_progress
from app.services.ai.task_utils import format_item_label


class VideoExtractor(BaseAIService):
    """Extract structured information from YouTube videos using Gemini's video understanding."""

    def __init__(self, db: Session):
        """Initialize the video extractor."""
        super().__init__(db)
        self.output_parser = JsonOutputParser(pydantic_object=ExtractionOutput)
        # Note: No setup_chain() since we construct HumanMessage manually

    async def process(
        self,
        content_item: ContentItem,
        *,
        text_timeout_seconds: float | None = None,
    ) -> Dict[str, Any]:
        """Extract structured information from video.

        Args:
            content_item: ContentItem with YouTube URL

        Returns:
            Dict with extraction results
        """
        # Check if video extraction is enabled
        if not settings.video_extraction_enabled:
            # Fallback to text extraction
            return await self._fallback_to_text_extraction(
                content_item,
                text_timeout_seconds=text_timeout_seconds,
            )

        try:
            # Get video extraction prompt
            prompt_info = PromptRegistry.get_video_extraction_prompt()

            # Construct HumanMessage with video URL
            message = HumanMessage(content=[
                {
                    "type": "text",
                    "text": prompt_info["template"]
                },
                {
                    "type": "media",
                    "file_uri": content_item.url,
                    "mime_type": "video/mp4"
                }
            ])

            # Run extraction with timeout
            timeout = settings.video_extraction_timeout_seconds
            llm = self._llm_with_timeout(timeout)
            result = await llm.ainvoke([message])

            # Parse JSON output
            parsed = self.output_parser.parse(result.content)

            # Save to database
            self._save_extraction(content_item.id, parsed)

            self.update_stats(True)

            return {
                "success": True,
                "extraction": parsed,
                "method": "video"
            }

        except (asyncio.TimeoutError, TimeoutError, DeadlineExceeded):
            error_msg = f"Video extraction timed out after {timeout}s for item {content_item.id}"
            self.update_stats(False, error_msg)

            # Fallback to text extraction
            return await self._fallback_to_text_extraction(
                content_item,
                text_timeout_seconds=text_timeout_seconds,
            )

        except OutputParserException as e:
            error_msg = f"Invalid JSON output for video {content_item.id}: {str(e)}"
            self.update_stats(False, error_msg)

            # Fallback to text extraction
            return await self._fallback_to_text_extraction(
                content_item,
                text_timeout_seconds=text_timeout_seconds,
            )

        except Exception as e:
            error_msg = f"Video extraction failed for item {content_item.id}: {str(e)}"
            self.update_stats(False, error_msg)

            # Fallback to text extraction
            return await self._fallback_to_text_extraction(
                content_item,
                text_timeout_seconds=text_timeout_seconds,
            )

    async def _fallback_to_text_extraction(
        self,
        content_item: ContentItem,
        *,
        text_timeout_seconds: float | None = None,
    ) -> Dict[str, Any]:
        """Fallback to text-based extraction using video description.

        Args:
            content_item: ContentItem to extract from

        Returns:
            Extraction result using text-based method
        """
        try:
            # Import here to avoid circular dependency
            from app.services.ai.extractor import StructuredExtractor

            extractor = StructuredExtractor(self.db)
            result = await extractor.process(
                content_item,
                timeout_seconds=text_timeout_seconds,
            )

            # Handle None result
            if result is None:
                return {
                    "success": False,
                    "error": "Text extraction returned None"
                }

            # Add metadata to indicate fallback
            if result.get("success"):
                result["method"] = "text_fallback"

            return result

        except Exception as e:
            # Catch any unexpected exceptions
            return {
                "success": False,
                "error": f"Fallback extraction failed: {str(e)}"
            }

    def _save_extraction(self, content_item_id: int, extraction: dict):
        """Save video extraction to ai_extractions table.

        Args:
            content_item_id: ID of content item
            extraction: Extraction result dict
        """
        prompt_info = PromptRegistry.get_video_extraction_prompt()

        # Delete existing extraction for this item
        self.db.query(AIExtraction).filter(
            AIExtraction.content_item_id == content_item_id
        ).delete()

        # Create new extraction
        ai_extraction = AIExtraction(
            content_item_id=content_item_id,
            created_at=datetime.utcnow(),
            model_provider="google",
            model_name="gemini-2.0-flash-exp",
            prompt_name=prompt_info["name"],
            prompt_version=prompt_info["version"],
            extracted_json=extraction
        )
        self.db.add(ai_extraction)
        self.db.commit()


# LangGraph node function
async def video_extract_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for video extraction.

    Args:
        state: Current state containing content_item, db

    Returns:
        Updated state with extraction_result
    """
    content_item = state["content_item"]
    db = state["db"]
    run = state.get("run")
    item_label = state.get("item_label") or format_item_label(content_item)

    # Only extract if classification succeeded
    if not (state.get("classification_result") or {}).get("success"):
        if run:
            append_run_task(
                run,
                task=f"Skipped extraction for item {content_item.id}",
                stage="extract",
                item_id=content_item.id,
                status="skipped",
                detail=item_label,
            )
            update_run_progress(
                run,
                phase="ai_processing",
                current_task=f"Skipping extraction for item {content_item.id} ({item_label})",
            )
            db.commit()
        return {
            **state,
            "extraction_result": {
                "success": False,
                "error": "Skipped due to classification failure"
            }
        }

    extractor = VideoExtractor(db)
    if run:
        append_run_task(
            run,
            task=f"Extracting item {content_item.id} (video)",
            stage="extract",
            item_id=content_item.id,
            status="started",
            detail=item_label,
        )
        update_run_progress(
            run,
            phase="ai_processing",
            current_task=f"Extracting item {content_item.id} (video) ({item_label})",
        )
        db.commit()
    result = await extractor.process(
        content_item,
        text_timeout_seconds=state.get("extraction_timeout_seconds"),
    )

    # Handle None result (defensive coding)
    if result is None:
        result = {
            "success": False,
            "error": "Video extraction returned None"
        }

    if run:
        append_run_task(
            run,
            task=f"Extraction finished for item {content_item.id} (video)",
            stage="extract",
            item_id=content_item.id,
            status="completed" if result.get("success") else "failed",
            detail=item_label if result.get("success") else result.get("error") or item_label,
        )
        db.commit()

    return {
        **state,
        "extraction_result": result,
        "error": result.get("error") if not result.get("success") else state.get("error")
    }
