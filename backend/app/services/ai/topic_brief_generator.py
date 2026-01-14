"""Topic brief generation service."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from datetime import datetime
from google.api_core.exceptions import DeadlineExceeded

from app.models.content_item import ContentItem
from app.models.topic import Topic
from app.models.topic_brief import TopicBrief
from app.services.ai.base import BaseAIService
from app.services.ai.prompts import PromptRegistry
from app.config import settings


class ContentReference(BaseModel):
    """Reference to a specific content item."""
    content_item_id: int
    title: str = Field(max_length=500)
    url: str
    key_point: str = Field(max_length=300)


class TopicBriefOutput(BaseModel):
    """Structured topic brief output."""
    summary_short: str = Field(min_length=100, max_length=500)
    summary_full: str = Field(min_length=300, max_length=2000)
    content_references: List[ContentReference] = Field(min_length=1, max_length=50)
    key_themes: List[str] = Field(max_length=5)
    significance: str = Field(max_length=400)


class TopicBriefGenerator(BaseAIService):
    """Generate executive briefs for topics."""

    def __init__(self, db: Session):
        """Initialize the generator."""
        super().__init__(db)
        self.output_parser = JsonOutputParser(pydantic_object=TopicBriefOutput)
        self.setup_chain()

    def setup_chain(self):
        """Set up the LangChain chain."""
        prompt_info = PromptRegistry.get_topic_brief_prompt()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert content analyst and executive briefing writer."),
            ("user", prompt_info["template"])
        ])

        self.chain = self.prompt | self.llm | self.output_parser

    async def generate_for_topic(
        self,
        topic: Topic,
        content_items: List[ContentItem],
        brief_id: int,
        timeout_seconds: int = 60
    ) -> TopicBrief:
        """Generate brief for a single topic with hierarchical batching.

        Args:
            topic: Topic object
            content_items: All content items for this topic in lookback period
            brief_id: ID of the brief this belongs to
            timeout_seconds: Timeout in seconds for AI generation

        Returns:
            Created TopicBrief object
        """
        # Get batch size from settings
        from app.models.app_settings import AppSettings as AppSettingsModel
        from app.schemas.settings import AppSettings

        settings_record = self.db.query(AppSettingsModel).first()
        if settings_record:
            try:
                settings = AppSettings.model_validate(settings_record.settings_json or {})
                batch_size = settings.brief.topic_brief_batch_size
            except Exception:
                batch_size = 10  # Default
        else:
            batch_size = 10  # Default

        # Limit to 50 most recent items (token management)
        if len(content_items) > 50:
            content_items = sorted(
                content_items,
                key=lambda x: x.published_at or datetime.min,
                reverse=True
            )[:50]

        # If items <= batch_size, use direct generation (no batching)
        if len(content_items) <= batch_size:
            return await self._generate_direct(topic, content_items, brief_id, timeout_seconds)

        # Split into batches
        batches = [
            content_items[i:i + batch_size]
            for i in range(0, len(content_items), batch_size)
        ]

        # Summarize each batch
        batch_summaries = []
        for i, batch in enumerate(batches, 1):
            try:
                summary = await self._summarize_batch(
                    batch,
                    i,
                    len(batches),
                    topic,
                    timeout_seconds=timeout_seconds / 2,
                )
                batch_summaries.append(summary)
            except (TimeoutError, DeadlineExceeded):
                # Skip failed batch but continue
                continue
            except Exception as e:
                # Log error but continue with other batches
                continue

        if not batch_summaries:
            raise Exception(f"All batch summarizations failed for topic: {topic.name}")

        # Create executive summary from batch summaries
        result = await self._synthesize_from_batches(
            topic, batch_summaries, content_items, timeout_seconds
        )

        # Save to database
        topic_brief = self._save_topic_brief(
            brief_id=brief_id,
            topic_id=topic.id,
            output=result,
            content_items=content_items,
        )

        return topic_brief

    async def _generate_direct(
        self,
        topic: Topic,
        content_items: List[ContentItem],
        brief_id: int,
        timeout_seconds: int
    ) -> TopicBrief:
        """Generate brief directly without batching (for small item sets).

        Args:
            topic: Topic object
            content_items: Content items for this topic
            brief_id: ID of the brief this belongs to
            timeout_seconds: Timeout in seconds

        Returns:
            Created TopicBrief object
        """
        # Format content for prompt
        content_text = self._format_content_items(content_items)

        # Generate with timeout
        try:
            llm = self._llm_with_timeout(timeout_seconds)
            chain = self.prompt | llm | self.output_parser
            result = await chain.ainvoke({
                "topic_name": topic.name,
                "topic_description": topic.description or "",
                "num_items": len(content_items),
                "content_items": content_text
            })
        except (TimeoutError, DeadlineExceeded):
            raise Exception(f"Topic brief generation timed out for topic: {topic.name}")
        except OutputParserException as e:
            raise Exception(f"Failed to parse AI output: {str(e)}")

        # Save to database
        topic_brief = self._save_topic_brief(
            brief_id=brief_id,
            topic_id=topic.id,
            output=result,
            content_items=content_items,
        )

        return topic_brief

    async def _summarize_batch(
        self,
        batch: List[ContentItem],
        batch_num: int,
        total_batches: int,
        topic: Topic,
        timeout_seconds: float | None = None,
    ) -> Dict[str, Any]:
        """Summarize a batch of content items.

        Args:
            batch: Batch of content items
            batch_num: Current batch number
            total_batches: Total number of batches
            topic: Topic object
            timeout_seconds: Timeout in seconds for batch generation

        Returns:
            Dict with batch_summary (str) and metadata
        """
        # Format batch items
        content_text = self._format_content_items(batch)

        # Use batch summarization prompt
        prompt_info = PromptRegistry.get_batch_summary_prompt()

        batch_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert content analyst."),
            ("user", prompt_info["template"])
        ])

        # Simple text output (not JSON) for batch summaries
        llm = self._llm_with_timeout(timeout_seconds)
        batch_chain = batch_prompt | llm

        result = await batch_chain.ainvoke({
            "topic_name": topic.name,
            "topic_description": topic.description or "",
            "batch_num": batch_num,
            "total_batches": total_batches,
            "num_items": len(batch),
            "content_items": content_text
        })

        return {
            "batch_summary": result.content,
            "batch_num": batch_num,
            "num_items": len(batch)
        }

    async def _synthesize_from_batches(
        self,
        topic: Topic,
        batch_summaries: List[Dict[str, Any]],
        all_items: List[ContentItem],
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Synthesize executive summary from batch summaries.

        Args:
            topic: Topic object
            batch_summaries: List of batch summary dicts
            all_items: All content items (for reference)
            timeout_seconds: Timeout in seconds

        Returns:
            TopicBriefOutput dict
        """
        # Format batch summaries
        batch_text = "\n\n".join([
            f"Batch {b['batch_num']} ({b['num_items']} items):\n{b['batch_summary']}"
            for b in batch_summaries
        ])

        # Use executive synthesis prompt
        prompt_info = PromptRegistry.get_executive_synthesis_prompt()

        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an executive briefing specialist."),
            ("user", prompt_info["template"])
        ])

        llm = self._llm_with_timeout(timeout_seconds)
        synthesis_chain = synthesis_prompt | llm | self.output_parser

        try:
            result = await synthesis_chain.ainvoke({
                "topic_name": topic.name,
                "topic_description": topic.description or "",
                "num_batches": len(batch_summaries),
                "total_items": len(all_items),
                "batch_summaries": batch_text
            })
        except (TimeoutError, DeadlineExceeded):
            raise Exception(f"Executive synthesis timed out for topic: {topic.name}")
        except OutputParserException as e:
            raise Exception(f"Failed to parse synthesis output: {str(e)}")

        return result

    def _format_content_items(self, items: List[ContentItem]) -> str:
        """Format content items for prompt."""
        formatted = []
        for i, item in enumerate(items, 1):
            # Get AI extraction if available
            extraction = item.ai_extractions[0] if item.ai_extractions else None
            summary = ""
            if extraction:
                extracted_json = (
                    extraction.extracted_json
                    if isinstance(extraction.extracted_json, dict)
                    else {}
                )
                bullets = extracted_json.get("summary_bullets", [])
                summary = " | ".join(bullets[:3]) if bullets else ""

            raw_text = item.raw_text or ""
            fallback_summary = raw_text[:200] if raw_text else "No summary available."
            formatted.append(
                f"{i}. (id:{item.id}) [{item.title}]({item.url})\n"
                f"   Published: {item.published_at}\n"
                f"   Summary: {summary or fallback_summary}\n"
            )

        return "\n".join(formatted)

    def _normalize_output(self, output: Any) -> Dict[str, Any]:
        if hasattr(output, "model_dump"):
            return output.model_dump()
        if isinstance(output, dict):
            return output
        return dict(output)

    def _sanitize_output(
        self,
        output: Dict[str, Any],
        content_items: List[ContentItem],
    ) -> Dict[str, Any]:
        allowed = {item.id: item for item in content_items}
        raw_refs = output.get("content_references") or []
        cleaned_refs: List[Dict[str, Any]] = []

        for ref in raw_refs:
            if not isinstance(ref, dict):
                continue
            raw_id = ref.get("content_item_id")
            item_id = None
            if isinstance(raw_id, int):
                item_id = raw_id
            elif isinstance(raw_id, str):
                digits = "".join(ch for ch in raw_id if ch.isdigit())
                if digits:
                    item_id = int(digits)

            if item_id not in allowed:
                title = (ref.get("title") or "").strip().lower()
                if title:
                    for candidate in content_items:
                        if (candidate.title or "").strip().lower() == title:
                            item_id = candidate.id
                            break

            if item_id not in allowed:
                continue

            item = allowed[item_id]
            cleaned_refs.append({
                "content_item_id": item_id,
                "title": item.title or ref.get("title") or "",
                "url": item.url or ref.get("url") or "",
                "key_point": ref.get("key_point") or "",
            })

        if not cleaned_refs and content_items:
            fallback_items = content_items[: min(3, len(content_items))]
            for item in fallback_items:
                cleaned_refs.append({
                    "content_item_id": item.id,
                    "title": item.title or "",
                    "url": item.url or "",
                    "key_point": "Key point not provided.",
                })

        output["content_references"] = cleaned_refs
        return output

    def _extract_cited_ids(self, summary_full: str) -> List[int]:
        """Extract all content item IDs cited in the summary text.

        Args:
            summary_full: The summary text with (id:XXX) citations

        Returns:
            List of unique content item IDs in citation order
        """
        import re

        cited_ids = []
        seen = set()

        # Match both (id:XXX) and (XXX) patterns
        # First pass: (id:XXX, YYY) format
        for match in re.finditer(r'\(id:([0-9,\s]+)\)', summary_full):
            for id_str in match.group(1).split(','):
                id_str = id_str.strip()
                if id_str.isdigit():
                    item_id = int(id_str)
                    # Skip years
                    if item_id >= 1900 and item_id <= 2099:
                        continue
                    if item_id not in seen:
                        cited_ids.append(item_id)
                        seen.add(item_id)

        # Second pass: (XXX, YYY) format without "id:" prefix
        for match in re.finditer(r'\(([0-9,\s]+)\)', summary_full):
            for id_str in match.group(1).split(','):
                id_str = id_str.strip()
                if id_str.isdigit():
                    item_id = int(id_str)
                    # Skip years
                    if item_id >= 1900 and item_id <= 2099:
                        continue
                    if item_id not in seen:
                        cited_ids.append(item_id)
                        seen.add(item_id)

        return cited_ids

    def _build_references_from_citations(
        self,
        cited_ids: List[int],
        ai_references: List[Dict],
        content_items: List[ContentItem],
    ) -> List[Dict[str, Any]]:
        """Build complete references list from all cited IDs.

        Args:
            cited_ids: All IDs cited in the summary text
            ai_references: The AI's original content_references (has key_point info)
            content_items: All content items available

        Returns:
            Complete list of references for all cited IDs
        """
        # Build lookup maps
        allowed = {item.id: item for item in content_items}
        ai_ref_map = {}
        for ref in ai_references:
            if isinstance(ref, dict) and "content_item_id" in ref:
                ai_ref_map[ref["content_item_id"]] = ref

        references = []
        for item_id in cited_ids:
            if item_id not in allowed:
                continue  # Skip invalid IDs

            item = allowed[item_id]
            ai_ref = ai_ref_map.get(item_id, {})

            references.append({
                "content_item_id": item_id,
                "title": item.title or ai_ref.get("title") or "",
                "url": item.url or ai_ref.get("url") or "",
                "key_point": ai_ref.get("key_point") or "Referenced in brief.",
            })

        return references

    def _convert_citations_to_numbers(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Convert (id:XXX) and (XXX) citations in summary_full to numbered format [N].

        Args:
            output: Output dict with summary_full and content_references

        Returns:
            Modified output dict with numbered citations
        """
        import re

        summary_full = output.get("summary_full", "")
        references = output.get("content_references", [])

        # Build mapping from content_item_id to reference number (1-indexed)
        id_to_number = {
            ref["content_item_id"]: idx + 1
            for idx, ref in enumerate(references)
        }

        # Build mapping from content_item_id to URL for creating links
        id_to_url = {
            ref["content_item_id"]: ref["url"]
            for ref in references
        }

        # Replace citations with [[N]] markdown links
        def replace_citation_list(match):
            # Get the IDs string (group 1)
            ids_str = match.group(1)

            # Extract all numeric IDs
            id_parts = ids_str.split(',')
            ids = []
            for id_str in id_parts:
                id_str = id_str.strip()
                if id_str.isdigit():
                    num = int(id_str)
                    # Skip 4-digit numbers that look like years (1900-2099)
                    if num >= 1900 and num <= 2099:
                        continue
                    ids.append(num)

            # Convert each ID to numbered link
            links = []
            for item_id in ids:
                if item_id in id_to_number:
                    number = id_to_number[item_id]
                    url = id_to_url.get(item_id, "")
                    links.append(f"[[{number}]]({url})")

            if links:
                return ''.join(links)
            return match.group(0)  # Keep original if no IDs found

        # First: Replace (id:XXX, YYY) patterns
        summary_full = re.sub(r'\(id:([0-9,\s]+)\)', replace_citation_list, summary_full)

        # Second: Replace (XXX, YYY) patterns (numbers without "id:" prefix)
        # This will match numbers in parentheses, but skip years via the filter in replace_citation_list
        summary_full = re.sub(r'\(([0-9,\s]+)\)', replace_citation_list, summary_full)

        output["summary_full"] = summary_full
        return output

    def _save_topic_brief(
        self,
        brief_id: int,
        topic_id: int,
        output: Dict[str, Any],
        content_items: List[ContentItem],
    ) -> TopicBrief:
        """Save topic brief to database."""
        output_dict = self._normalize_output(output)

        # Extract all cited IDs from summary_full and build complete references
        summary_full = output_dict.get("summary_full", "")
        cited_ids = self._extract_cited_ids(summary_full)
        ai_references = output_dict.get("content_references", [])
        complete_references = self._build_references_from_citations(
            cited_ids, ai_references, content_items
        )
        output_dict["content_references"] = complete_references

        # Convert (id:XXX) citations to numbered format [N]
        output_dict = self._convert_citations_to_numbers(output_dict)

        # Extract content item IDs from references
        content_item_ids = [
            ref["content_item_id"]
            for ref in output_dict["content_references"]
        ]

        # Store all AI output in content_references JSONB field
        content_references_json = {
            "references": output_dict["content_references"],
            "key_themes": output_dict.get("key_themes", []),
            "significance": output_dict.get("significance", "")
        }

        topic_brief = TopicBrief(
            brief_id=brief_id,
            topic_id=topic_id,
            summary_short=output_dict["summary_short"],
            summary_full=output_dict["summary_full"],
            content_item_ids=content_item_ids,
            content_references=content_references_json,
            model_provider=settings.llm_provider,
            model_name=settings.llm_model,
            prompt_version="v1.0"
        )

        self.db.add(topic_brief)
        self.db.commit()
        self.db.refresh(topic_brief)

        return topic_brief

    async def process(self, content_item: ContentItem) -> Dict[str, Any]:
        """Not used for topic briefs (required by base class)."""
        raise NotImplementedError("Use generate_for_topic instead")
