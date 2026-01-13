"""Structured extraction service using LangGraph."""

import asyncio
from typing import Dict, Any, List, Optional, Literal
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from google.api_core.exceptions import DeadlineExceeded
from datetime import datetime

from app.models.content_item import ContentItem
from app.models.ai_extraction import AIExtraction
from app.config import settings
from app.services.ai.base import BaseAIService
from app.services.ai.prompts import PromptRegistry
from app.services.run_progress import append_run_task, update_run_progress
from app.services.ai.task_utils import format_item_label


class KeyClaim(BaseModel):
    """A key claim with confidence level."""
    claim: str = Field(max_length=500)
    confidence: Literal["low", "med", "high"]


class ExtractionOutput(BaseModel):
    """Structured extraction output schema."""
    summary_bullets: List[str] = Field(min_length=2, max_length=5)
    why_it_matters: List[str] = Field(min_length=1, max_length=2)
    key_claims: List[KeyClaim] = Field(max_length=5)
    novelty: Literal["new", "update", "recurring"]
    confidence_overall: Literal["low", "med", "high"]
    follow_ups: Optional[List[str]] = Field(default=None, max_length=3)

    @field_validator('summary_bullets')
    @classmethod
    def validate_bullet_length(cls, v):
        """Validate bullet point length."""
        for bullet in v:
            if len(bullet) > 200:
                raise ValueError('Bullet point too long (max 200 chars)')
        return v


class StructuredExtractor(BaseAIService):
    """Structured extraction service using structured output."""

    def __init__(self, db: Session):
        """Initialize the extractor."""
        super().__init__(db)
        self.output_parser = JsonOutputParser(pydantic_object=ExtractionOutput)
        self.setup_chain()

    def setup_chain(self):
        """Set up the LangChain chain with structured output."""
        prompt_info = PromptRegistry.get_extraction_prompt()

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert content analyst."),
            ("user", prompt_info["template"])
        ])

        # Create chain
        self.chain = self.prompt | self.llm | self.output_parser

    async def process(
        self,
        content_item: ContentItem,
        *,
        timeout_seconds: float | None = None,
    ) -> Dict[str, Any]:
        """Extract structured information from content item.

        Args:
            content_item: ContentItem to extract from

        Returns:
            Dict with extraction results
        """
        try:
            # Get content text
            content_text = content_item.raw_text or content_item.title

            # Run extraction
            timeout = (
                float(timeout_seconds)
                if timeout_seconds is not None
                else float(settings.ai_extraction_timeout_seconds)
            )
            chain = self.prompt | self._llm_with_timeout(timeout) | self.output_parser
            result = await chain.ainvoke({
                    "title": content_item.title,
                    "url": content_item.url,
                    "content": content_text
                })

            # Save to database
            self._save_extraction(content_item.id, result)

            self.update_stats(True)

            return {
                "success": True,
                "extraction": result
            }

        except (asyncio.TimeoutError, TimeoutError, DeadlineExceeded):
            timeout = (
                float(timeout_seconds)
                if timeout_seconds is not None
                else float(settings.ai_extraction_timeout_seconds)
            )
            error_msg = f"Extraction timed out after {int(timeout)}s for item {content_item.id}"
            self.update_stats(False, error_msg)

            # Try retry with simpler prompt
            try:
                result = await self._retry_with_fallback(
                    content_item,
                    timeout_seconds=timeout,
                )
                return {
                    "success": True,
                    "extraction": result,
                    "retried": True
                }
            except Exception as retry_error:
                return {
                    "success": False,
                    "error": f"{error_msg}. Retry also failed: {str(retry_error)}"
                }

        except OutputParserException as e:
            error_msg = f"Invalid JSON output for item {content_item.id}: {str(e)}"
            self.update_stats(False, error_msg)

            # Try retry with simpler prompt
            try:
                result = await self._retry_with_fallback(
                    content_item,
                    timeout_seconds=(
                        float(timeout_seconds)
                        if timeout_seconds is not None
                        else float(settings.ai_extraction_timeout_seconds)
                    ),
                )
                return {
                    "success": True,
                    "extraction": result,
                    "retried": True
                }
            except Exception as retry_error:
                return {
                    "success": False,
                    "error": f"{error_msg}. Retry also failed: {str(retry_error)}"
                }

        except Exception as e:
            error_msg = f"Extraction failed for item {content_item.id}: {str(e)}"
            self.update_stats(False, error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    async def _retry_with_fallback(
        self,
        content_item: ContentItem,
        *,
        timeout_seconds: float | None = None,
    ) -> dict:
        """Retry extraction with simplified requirements.

        Args:
            content_item: ContentItem to extract from

        Returns:
            Extraction result
        """
        # Simplified prompt for retry
        simplified_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a content summarizer. Extract key information concisely."),
            ("user", """Summarize this content in JSON format:

Title: {title}
Content: {content}

Return JSON:
{{
  "summary_bullets": ["point1", "point2"],
  "why_it_matters": ["reason1"],
  "key_claims": [],
  "novelty": "recurring",
  "confidence_overall": "med",
  "follow_ups": []
}}""")
        ])

        simplified_chain = (
            simplified_prompt
            | self._llm_with_timeout(timeout_seconds)
            | self.output_parser
        )

        content_text = content_item.raw_text or content_item.title
        result = await simplified_chain.ainvoke({
            "title": content_item.title,
            "content": content_text[:500]  # Limit content length
        })

        # Save to database
        self._save_extraction(content_item.id, result)

        return result

    def _save_extraction(self, content_item_id: int, extraction: dict):
        """Save extraction to ai_extractions table.

        Args:
            content_item_id: ID of content item
            extraction: Extraction result dict
        """
        prompt_info = PromptRegistry.get_extraction_prompt()

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
async def extract_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for structured extraction.

    Args:
        state: Current state containing content_item, classification_result, db

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

    extractor = StructuredExtractor(db)
    if run:
        append_run_task(
            run,
            task=f"Extracting item {content_item.id} (text)",
            stage="extract",
            item_id=content_item.id,
            status="started",
            detail=item_label,
        )
        update_run_progress(
            run,
            phase="ai_processing",
            current_task=f"Extracting item {content_item.id} (text) ({item_label})",
        )
        db.commit()
    result = await extractor.process(
        content_item,
        timeout_seconds=state.get("extraction_timeout_seconds"),
    )

    # Handle None result (defensive coding)
    if result is None:
        result = {
            "success": False,
            "error": "Text extraction returned None"
        }

    if run:
        append_run_task(
            run,
            task=f"Extraction finished for item {content_item.id} (text)",
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
