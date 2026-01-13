# Signal Digest \- Minimal MVP Spec

## 0\) MVP Goal

Build a distraction-free daily brief that pulls:

- Web news (RSS first)  
- YouTube videos from a curated list of channels  
- X posts from a curated list of users (via [https://twitterapi.io/](https://twitterapi.io/))

Then uses an AI pipeline to extract "pure signal" per configured topics and delivers a finite Morning Brief you can consume quickly, without scrolling/searching.

Manual trigger for fetch \+ processing in the UI (cron/scheduler later).

---

## 1\) MVP Success Criteria

- I can configure:  
  - Topics  
  - RSS feeds  
  - YouTube channels  
  - X accounts  
- I can click “Run ingestion \+ AI” and get a Morning Brief for today.  
- Morning Brief shows a capped list (default 15 items), each with:  
  - Title  
  - 2–5 bullet summary  
  - Why it matters (1–2 bullets)  
  - Topic tags  
  - Confidence (low/med/high)  
  - Links to original endpoints (news/YT/X)  
- No doomscrolling patterns:  
  - No infinite feed  
  - No autoplay  
  - Hard caps per brief and per topic

---

## 2\) Scope (Minimal)

### Included

- CRUD config: Topics \+ Endpoints  
- Ingestion to Postgres (normalized content items)  
- AI processing (LangChain \+ Gemini 3 Flash):  
  - topic classification (multi-label)  
  - structured extraction ("pure signal")  
- Basic dedupe  
- Morning Brief \+ Topic Explorer UI  
- Manual runs \+ run history/status

### Excluded (Post-MVP)

- Scheduling/cron/Celery  
- Embedding-based clustering into “story clusters”  
- Multi-user/team features  
- Feedback training loop  
- Complex scraping/paywalls  
- Notifications/mobile

---

## 3\) Architecture

### Frontend

- **Next.js \+ React**  
- **shadcn/ui \+ Tailwind**  
- Pages:  
  - `/brief` (Morning Brief)  
  - `/explore` (Topic Explorer)  
  - `/topics` (Topics CRUD)  
  - `/endpoints` (Endpoints CRUD)  
  - `/runs` (Manual triggers \+ history)

### Backend

- **Python API** (FastAPI recommended)  
- **Postgres** as source of truth  
- Manual job runner via API endpoints (synchronous MVP), with persisted logs

### External Integrations

- RSS ingestion: feedparser \+ requests  
- YouTube ingestion: channel RSS (fastest MVP; avoids API keys)  
- X ingestion: twitterapi.io for timelines per configured account

---

## 4\) Data Model (Postgres — Minimal)

### topics

- id  
- name  
- description  
- include\_rules (text)  
- exclude\_rules (text)  
- priority (int)  
- enabled (bool)

### endpoints

- id  
- connector_type: `rss | youtube_channel | x_user`  
- name  
- target (rss\_url | channel\_url/id | x\_handle)  
- enabled (bool)  
- weight (int)  
- notes (text)

### connector\_queries

- id  
- connector\_type: `tavily`  
- topic\_id (fk)  
- query  
- options\_json (jsonb)  
- created\_at

### content\_items

- id  
- endpoint\_id (fk, nullable)  
- connector\_query\_id (fk, nullable)  
- connector\_type  
- external\_id (tweet id / video id / guid)  
- url  
- title  
- author (nullable)  
- published\_at  
- fetched\_at  
- raw\_text (nullable) — article text / transcript / tweet text  
- raw\_json (jsonb) — full payload for future  
- lang (nullable)  
- hash (dedupe)

### topic\_assignments

- id  
- content\_item\_id (fk)  
- topic\_id (fk)  
- score (float)  
- rationale\_short (text)

### ai\_extractions

- id  
- content\_item\_id (fk)  
- created\_at  
- model\_provider: `"google"`  
- model\_name: `"gemini-3-flash"`  
- prompt\_name  
- prompt\_version  
- extracted\_json (jsonb)  
- quality\_score (nullable)

### briefs

- id  
- date  
- mode: `"morning"`  
- created\_at

### brief\_items

- id  
- brief\_id (fk)  
- content\_item\_id (fk)  
- rank (int)  
- reason\_included (text)

### runs (recommended)

- id  
- run\_type: `ingest | ai | build_brief`  
- started\_at, finished\_at  
- status: `success | failed`  
- stats\_json (jsonb)  
- error\_text (nullable)

---

## 5\) Normalization Rule: One Internal Content Type

All ingested items become `content_items`, regardless of source:

- RSS entry → content\_item  
- YouTube video → content\_item (raw\_text \= transcript if available later; MVP can omit transcript)  
- X post → content\_item (raw\_text \= tweet text)

---

## 6\) Ingestion Rules (MVP)

- Fetch window: last 48h  
- Per-source fetch limit (defaults):  
  - RSS: 30  
  - YouTube channel: 10  
  - X user: 20  
- Dedupe:  
  - primary: same `external_id` OR same `url`  
  - secondary: title hash match within 48h

---

## 7\) AI Pipeline (LangChain \+ Gemini 3 Flash)

### Model choice

- Use **Gemini 3 Flash** for all AI tasks in MVP  
- Orchestration via **LangChain**

### A) Topic Classification (multi-label)

**Inputs**

- title  
- raw\_text (if present; otherwise snippet/description)  
- topic definitions (include/exclude rules)

**Outputs**

- topic\_assignments: (topic\_id, score, rationale\_short)  
- top-k topics per item (default k=3–5)

### B) Structured Extraction (“Pure Signal”)

**Inputs**

- title  
- raw\_text (or best available text)  
- URL (for provenance)

**Output JSON schema**

- summary\_bullets: string\[\]  
- why\_it\_matters: string\[\]  
- key\_claims: \[{ claim: string, confidence: "low"|"med"|"high" }\]  
- novelty: "new"|"update"|"recurring"  
- confidence\_overall: "low"|"med"|"high"  
- follow\_ups (optional): string\[\]

### LangChain handling (minimal but robust)

- Structured output enforcement \+ JSON validation  
- Retry once on invalid JSON  
- Low temperature (reduce drift)  
- Prompts versioned: prompt\_name \+ prompt\_version stored per extraction

### Brief builder (non-AI in MVP)

Deterministic selection:

- rank by: topic priority, novelty, recency, endpoint weight  
- enforce caps:  
  - total items: 15  
  - per-topic cap: 3

---

## 8\) UX / UI Requirements (MVP)

### Morning Brief (`/brief`)

- Header: date \+ “Run now” button  
- Finite list of cards (no infinite scroll)  
- Each card shows:  
  - title  
  - summary bullets  
  - why it matters  
  - topic chips  
  - confidence badge  
  - “Open item” links  
- Optional: “Mark as read” (can be local-only for MVP)

### Endpoints (`/endpoints`)

- Tabs: RSS / YouTube / X  
- Add/edit/disable endpoint  
- Show last fetch time and item count (basic)

### Topics (`/topics`)

- Add/edit:  
  - name, description  
  - include/exclude rules  
  - priority, enabled

### Runs (`/runs`)

- Buttons:  
  - Ingest all  
  - Run AI  
  - Build today’s brief  
- Run history with status \+ counts \+ errors

### Explore (`/explore`)

- Filter by topic \+ date range  
- List items with extracted summaries

---

## 9\) Minimal API Endpoints

### Config

- GET/POST `/api/topics`  
    
- GET/PUT/DELETE `/api/topics/{id}`  
    
- GET/POST `/api/endpoints`  
    
- GET/PUT/DELETE `/api/endpoints/{id}`

### Runs

- POST `/api/run/ingest`  
- POST `/api/run/ai`  
- POST `/api/run/build-brief?date=YYYY-MM-DD&mode=morning`  
- GET  `/api/runs`

### Read views

- GET `/api/brief?date=YYYY-MM-DD&mode=morning`  
- GET `/api/explore?topic_id=...&from=...&to=...`

---

## 10\) Default Settings (MVP)

- Morning brief max items: 15  
- Per-topic cap: 3  
- Ingestion window: 48h  
- Fetch limits:  
  - RSS feed: 30  
  - YouTube channel: 10  
  - X user: 20

---

## 11\) Implementation Phases (Minimal)

### Phase 1 — Skeleton \+ CRUD

- Next.js \+ shadcn pages  
- FastAPI \+ Postgres \+ migrations  
- Topics/Endpoints CRUD

### Phase 2 — Ingestion

- RSS ingestion end-to-end  
- YouTube channel ingestion (RSS-based)  
- X ingestion via twitterapi.io  
- Persistence \+ dedupe

### Phase 3 — AI \+ Brief

- LangChain chains for classification \+ extraction (Gemini 3 Flash)  
- Morning brief builder  
- Brief UI polish \+ Runs page

---

## 12\) Out of Scope But Designed For

- Embedding-based clustering into story clusters  
- AI “final editor” pass for the brief  
- User feedback loop (“this was noise”) to refine prompts/scoring  
- Scheduling \+ notifications  
- Multiple brief modes (morning/evening) and time-of-day topic preferences
