"""Topic classification service using LangGraph."""

import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from google.api_core.exceptions import DeadlineExceeded

from app.models.topic import Topic
from app.models.topic_assignment import TopicAssignment
from app.models.content_item import ContentItem
from app.config import settings
from app.services.ai.base import BaseAIService
from app.services.ai.prompts import PromptRegistry
from app.services.ai.constants import MAX_TOPICS_PER_ITEM, MIN_CLASSIFICATION_SCORE
from app.services.run_progress import append_run_task, update_run_progress
from app.services.ai.task_utils import format_item_label


class TopicAssignmentOutput(BaseModel):
    """Structured output for a single topic assignment."""
    topic_id: int
    score: float = Field(ge=0.0, le=1.0)
    rationale_short: str = Field(max_length=500)


class ClassificationOutput(BaseModel):
    """Complete classification result."""
    assignments: List[TopicAssignmentOutput] = Field(max_items=MAX_TOPICS_PER_ITEM)


class TopicClassifier(BaseAIService):
    """Topic classification service using structured output."""

    def __init__(self, db: Session):
        """Initialize the classifier."""
        super().__init__(db)
        self.output_parser = JsonOutputParser(pydantic_object=ClassificationOutput)
        self.setup_chain()

    def setup_chain(self):
        """Set up the LangChain chain with structured output."""
        prompt_info = PromptRegistry.get_classification_prompt()

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert content classifier."),
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
        """Classify content item against all enabled topics.

        Args:
            content_item: ContentItem to classify

        Returns:
            Dict with classification results
        """
        try:
            # Get all enabled topics
            topics = self.db.query(Topic).filter(Topic.enabled == True).all()

            if not topics:
                return {
                    "success": True,
                    "assignments": [],
                    "message": "No enabled topics found"
                }

            # Format topics for prompt
            topics_str = self._format_topics(topics)

            # Get content text - prefer extraction summary for better classification
            content_text = content_item.raw_text or content_item.title

            # Check if we have an extraction with better content
            if content_item.ai_extractions:
                extraction = content_item.ai_extractions[0]
                bullets = extraction.extracted_json.get("summary_bullets", [])
                if bullets:
                    # Use extracted summary for better classification
                    content_text = " | ".join(bullets)

            # Run classification
            timeout = (
                float(timeout_seconds)
                if timeout_seconds is not None
                else float(settings.ai_classification_timeout_seconds)
            )
            chain = self.prompt | self._llm_with_timeout(timeout) | self.output_parser
            result = await chain.ainvoke({
                    "title": content_item.title,
                    "content": content_text,
                    "topics": topics_str
                })

            # Filter by minimum score
            filtered_assignments = [
                a for a in result["assignments"]
                if a["score"] >= MIN_CLASSIFICATION_SCORE
            ]

            # Save to database
            if filtered_assignments:
                self._save_assignments(content_item.id, filtered_assignments)

            self.update_stats(True)

            return {
                "success": True,
                "assignments": filtered_assignments,
                "count": len(filtered_assignments)
            }

        except (asyncio.TimeoutError, TimeoutError, DeadlineExceeded):
            timeout = (
                float(timeout_seconds)
                if timeout_seconds is not None
                else float(settings.ai_classification_timeout_seconds)
            )
            error_msg = (
                f"Classification timed out after {int(timeout)}s for item {content_item.id}"
            )
            self.update_stats(False, error_msg)
            return {
                "success": False,
                "error": error_msg,
                "assignments": []
            }

        except OutputParserException as e:
            error_msg = f"Invalid JSON output for item {content_item.id}: {str(e)}"
            self.update_stats(False, error_msg)
            return {
                "success": False,
                "error": error_msg,
                "assignments": []
            }

        except Exception as e:
            error_msg = f"Classification failed for item {content_item.id}: {str(e)}"
            self.update_stats(False, error_msg)
            return {
                "success": False,
                "error": error_msg,
                "assignments": []
            }

    def _format_topics(self, topics: List[Topic]) -> str:
        """Format topics for prompt.

        Args:
            topics: List of Topic objects

        Returns:
            Formatted string of topics
        """
        formatted = []
        for topic in topics:
            topic_str = f"ID: {topic.id}, Name: {topic.name}"
            if topic.description:
                topic_str += f", Description: {topic.description}"
            if topic.include_rules:
                topic_str += f", Include: {topic.include_rules}"
            if topic.exclude_rules:
                topic_str += f", Exclude: {topic.exclude_rules}"
            formatted.append(topic_str)
        return "\n".join(formatted)

    def _save_assignments(self, content_item_id: int, assignments: List[dict]):
        """Save topic assignments to database.

        Args:
            content_item_id: ID of content item
            assignments: List of assignment dicts
        """
        # Delete existing assignments for this item
        self.db.query(TopicAssignment).filter(
            TopicAssignment.content_item_id == content_item_id
        ).delete()

        # Create new assignments
        for assignment in assignments:
            topic_assignment = TopicAssignment(
                content_item_id=content_item_id,
                topic_id=assignment["topic_id"],
                score=assignment["score"],
                rationale_short=assignment["rationale_short"]
            )
            self.db.add(topic_assignment)

        self.db.commit()


# LangGraph node function
async def classify_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for topic classification.

    Args:
        state: Current state containing content_item, topics, db

    Returns:
        Updated state with classification_result
    """
    content_item = state["content_item"]
    db = state["db"]
    run = state.get("run")
    item_label = state.get("item_label") or format_item_label(content_item)

    if run:
        append_run_task(
            run,
            task=f"Classifying item {content_item.id}",
            stage="classify",
            item_id=content_item.id,
            status="started",
            detail=item_label,
        )
        update_run_progress(
            run,
            phase="ai_processing",
            current_task=f"Classifying item {content_item.id} ({item_label})",
        )
        db.commit()

    classifier = TopicClassifier(db)
    result = await classifier.process(
        content_item,
        timeout_seconds=state.get("classification_timeout_seconds"),
    )

    # Handle None result (defensive coding)
    if result is None:
        result = {
            "success": False,
            "error": "Classification returned None"
        }

    if run:
        append_run_task(
            run,
            task=f"Classification finished for item {content_item.id}",
            stage="classify",
            item_id=content_item.id,
            status="completed" if result.get("success") else "failed",
            detail=item_label if result.get("success") else result.get("error") or item_label,
        )
        db.commit()

    return {
        **state,
        "classification_result": result,
        "error": result.get("error") if not result.get("success") else state.get("error")
    }
