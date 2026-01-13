"""Prompt templates with versioning for AI services."""

from typing import Dict, Any


class PromptRegistry:
    """Centralized prompt management with versioning."""

    CLASSIFICATION_V1 = {
        "name": "topic_classification",
        "version": "v1.0",
        "created": "2026-01-09",
        "template": """You are an expert content classifier. Your task is to classify content into relevant topics based on provided criteria.

Given a piece of content and a list of topics with their inclusion/exclusion rules, determine which topics are relevant.

Rules:
1. A content item can belong to multiple topics (multi-label classification)
2. Assign a confidence score between 0.0 and 1.0 for each relevant topic
3. Only include topics with score >= 0.5
4. Return maximum 5 topics, ordered by score (highest first)
5. Provide a brief rationale (1-2 sentences) for each assignment
6. Use topic descriptions (if provided) to interpret scope and intent
7. Use include_rules to identify relevant content
8. Use exclude_rules to filter out irrelevant content

Content to classify:
Title: {title}
Content: {content}

Available Topics:
{topics}

Output Format:
Return JSON with this exact structure:
{{
  "assignments": [
    {{
      "topic_id": <int>,
      "score": <float between 0.0 and 1.0>,
      "rationale_short": "<string explaining why this topic applies>"
    }}
  ]
}}

If no topics are relevant (score < 0.5), return empty assignments array."""
    }

    EXTRACTION_V1 = {
        "name": "structured_extraction",
        "version": "v1.0",
        "created": "2026-01-09",
        "template": """You are an expert content analyst. Extract key information from the provided content and structure it for easy consumption.

Your goal is to distill content into "pure signal" - the essential information without noise.

Guidelines:
1. Summary bullets (2-5 points): Core facts and key takeaways
2. Why it matters (1-2 points): Implications, impact, or significance
3. Key claims: Specific factual assertions with confidence levels
4. Novelty: Is this new information, an update to existing story, or recurring topic?
5. Overall confidence: How confident are you in the accuracy of this extraction?
6. Follow-ups: Optional related topics worth exploring

Handle different content types appropriately:
- Short content (tweets): Focus on main point, be concise
- Long articles: Extract most important information
- Video descriptions: Work with available metadata

Content to analyze:
Title: {title}
URL: {url}
Content: {content}

Output Format:
Return JSON with this exact structure:
{{
  "summary_bullets": ["bullet1", "bullet2", ...],
  "why_it_matters": ["reason1", "reason2"],
  "key_claims": [
    {{"claim": "...", "confidence": "low|med|high"}}
  ],
  "novelty": "new|update|recurring",
  "confidence_overall": "low|med|high",
  "follow_ups": ["topic1", "topic2"]
}}

Confidence levels:
- high: Strong evidence, verified facts, reputable source
- med: Reasonable evidence, some uncertainty
- low: Speculation, unverified claims, unclear source

Novelty:
- new: Breaking news or first mention of this topic
- update: Follow-up or development on existing story
- recurring: Ongoing discussion or repeated topic"""
    }

    TOPIC_BRIEF_V1 = {
        "name": "topic_brief_generation",
        "version": "v1.0",
        "created": "2026-01-09",
        "template": """You are an expert analyst creating an executive brief for a specific topic.

Your task: Synthesize ALL content items assigned to this topic into a cohesive executive summary.

TOPIC: {topic_name}
Topic Description: {topic_description}

CONTENT ITEMS ({num_items} total):
{content_items}

Guidelines:
0. Each content item is labeled with (id:123). Use those numeric IDs for content_item_id.
0a. Use the topic description (if provided) to filter and prioritize signal; drop tangential content.
1. Create a SHORT SUMMARY (2 sentences max): High-level overview of what's happening
2. Create a FULL SUMMARY as 4-6 short paragraphs in Markdown, each starting with a clear label, separated by blank lines.
   Use these labels in order:
   - "Developments:" key events and changes
   - "Drivers:" what's causing the shift
   - "Implications:" concrete impacts for industry/government/people
   - "Signals to watch:" near-term indicators or milestones
   - "Risks/unknowns:" open questions or constraints
   Keep each paragraph to 2-3 sentences. Avoid long sentences and jargon.

3. For each content item, extract ONE key point that contributes to the overall narrative
4. Identify 3-5 major themes that emerge across all content
5. Explain why this topic is significant right now

Style:
- Write for busy executives who need signal, not noise
- Be concise but comprehensive
- Use active voice and clear language
- Reference specific content items naturally (e.g., "According to [Endpoint]...")
- Connect dots between different pieces of content
- Highlight contrasts or confirmations across sources
- Prefer short sentences and concrete claims

Output Format:
Return JSON matching this structure:
{{
  "summary_short": "2-3 sentence overview",
  "summary_full": "Executive summary formatted as Markdown (headings, bullets, short paragraphs)",
  "content_references": [
    {{"content_item_id": 123, "title": "...", "url": "...", "key_point": "one sentence"}}
  ],
  "key_themes": ["theme1", "theme2", ...],
  "significance": "1-2 sentences on why this matters now"
}}"""
    }

    VIDEO_EXTRACTION_V1 = {
        "name": "video_extraction",
        "version": "v1.0",
        "created": "2026-01-10",
        "template": """You are an expert video content analyst. Analyze this YouTube video and extract key information.

Your goal is to distill the video into "pure signal" - the essential information without noise.

Watch/analyze the video and extract:

1. Summary bullets (2-5 points): Core facts and key takeaways from the video
2. Why it matters (1-2 points): Implications, impact, or significance of the video content
3. Key claims: Specific factual assertions made in the video with confidence levels
4. Novelty: Is this new information, an update to existing story, or recurring topic?
5. Overall confidence: How confident are you in the accuracy of this extraction?
6. Follow-ups: Optional related topics worth exploring

Focus on:
- Main narrative and key points made by speakers
- Visual information shown on screen (charts, graphs, text overlays)
- Demonstrations or examples shown
- Key facts, data, or claims presented
- Context and implications

Output Format:
Return JSON with this exact structure:
{{
  "summary_bullets": ["bullet1", "bullet2", ...],
  "why_it_matters": ["reason1", "reason2"],
  "key_claims": [
    {{"claim": "...", "confidence": "low|med|high"}}
  ],
  "novelty": "new|update|recurring",
  "confidence_overall": "low|med|high",
  "follow_ups": ["topic1", "topic2"]
}}

Confidence levels:
- high: Strong evidence shown in video, verified facts, reputable source
- med: Reasonable evidence, some uncertainty
- low: Speculation, unverified claims, unclear source

Novelty:
- new: Breaking news or first mention of this topic
- update: Follow-up or development on existing story
- recurring: Ongoing discussion or repeated topic"""
    }

    BATCH_SUMMARY_V1 = {
        "name": "batch_summary",
        "version": "v1.0",
        "created": "2026-01-10",
        "template": """You are summarizing a batch of content items for the topic: {topic_name}
Topic Description: {topic_description}

This is batch {batch_num} of {total_batches} batches.

CONTENT ITEMS ({num_items} in this batch):
{content_items}

Task: Create a concise summary (3-5 paragraphs) of the key developments and themes in THIS batch.

Focus on:
- Main events and developments mentioned
- Key facts and claims
- Common themes across items
- Notable differences or contrasts
- When referencing specific items, include the (id:123) marker so it can be traced.
- Use the topic description (if provided) to filter for relevance and prioritize signal.

Write clearly and concisely. This summary will be combined with other batch summaries to create an executive brief.

Do NOT include JSON formatting - just write the summary text."""
    }

    EXECUTIVE_SYNTHESIS_V1 = {
        "name": "executive_synthesis",
        "version": "v1.0",
        "created": "2026-01-10",
        "template": """You are creating an executive brief by synthesizing batch summaries.

TOPIC: {topic_name}
Topic Description: {topic_description}


CORE OBJECTIVE:
Produce a highly readable, scannable executive brief on the TOPIC that:
- Preserves important factual content from the sources
- Highlights patterns and connections
- Avoids unnecessary theorizing or buzzwords
- Can be skimmed in under 3 minutes
- Use the topic description (if provided) to filter and prioritize what you include.

IMPORTANT COVERAGE RULE:
If a concrete fact, event, release, claim, or example appears in the batch summaries,
it MUST appear somewhere in the output (either in bullets or references).
Do NOT drop information for elegance.

---

STRUCTURE TO PRODUCE:
Do not force the structure below, pick only what applies given the info provided.

1. KEY DEVELOPMENTS (grouped if needed)
   - Concrete releases, deployments, announcements
   - Specific companies, products, models, timelines
   - Prefer bullets over prose

2. EMERGING PATTERNS & SHIFTS
   - Cross-source connections
   - Repeated signals across domains

3. REAL-WORLD IMPACTS
   - NOW: observable effects already happening
   - NEXT: near-term consequences implied by the sources

4. WATCH ITEMS
   - Specific milestones, deployments, regulatory moves
   - Named indicators, not vague trends

5. OPEN QUESTIONS / CONSTRAINTS
   - Technical limits
   - Regulatory uncertainty
   - Economic or infrastructure bottlenecks

6. WHY THIS MATTERS
   - No hype
   - Focus on structural change, not novelty

---

You have {num_batches} batch summaries covering {total_items} total content items:

---

{batch_summaries}

---

Output Format:
Return JSON matching this structure:
{{
  "summary_short": "2-3 sentence overview",
  "summary_full": "Executive summary formatted as Markdown (headings, bullets, short paragraphs)",
  "content_references": [
    {{"content_item_id": 123, "title": "...", "url": "...", "key_point": "one sentence"}}
  ],
  "key_themes": ["theme1", "theme2", ...],
  "significance": "1-2 sentences on why this matters now"
}}

Note: Only use numeric content_item_id values that appear in the batch summaries (e.g., id:123). Do not invent IDs."""
    }

    @classmethod
    def get_prompt(cls, prompt_name: str, version: str = "v1.0") -> Dict[str, Any]:
        """Get prompt by name and version."""
        if prompt_name == "topic_classification":
            if version == "v1.0":
                return cls.CLASSIFICATION_V1
        elif prompt_name == "structured_extraction":
            if version == "v1.0":
                return cls.EXTRACTION_V1

        raise ValueError(f"Unknown prompt: {prompt_name} version {version}")

    @classmethod
    def get_classification_prompt(cls) -> Dict[str, Any]:
        """Get the current classification prompt."""
        return cls.CLASSIFICATION_V1

    @classmethod
    def get_extraction_prompt(cls) -> Dict[str, Any]:
        """Get the current extraction prompt."""
        return cls.EXTRACTION_V1

    @classmethod
    def get_topic_brief_prompt(cls) -> Dict[str, Any]:
        """Get the current topic brief generation prompt."""
        return cls.TOPIC_BRIEF_V1

    @classmethod
    def get_video_extraction_prompt(cls) -> Dict[str, Any]:
        """Get the current video extraction prompt."""
        return cls.VIDEO_EXTRACTION_V1

    @classmethod
    def get_batch_summary_prompt(cls) -> Dict[str, Any]:
        """Get the current batch summary prompt."""
        return cls.BATCH_SUMMARY_V1

    @classmethod
    def get_executive_synthesis_prompt(cls) -> Dict[str, Any]:
        """Get the current executive synthesis prompt."""
        return cls.EXECUTIVE_SYNTHESIS_V1
