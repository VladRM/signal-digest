/**
 * TypeScript type definitions for Signal Digest
 */

export type ConnectorType = "rss" | "youtube_channel" | "x_user" | "tavily";
export type EndpointConnectorType = Exclude<ConnectorType, "tavily">;

export interface Topic {
  id: number;
  name: string;
  description?: string;
  include_rules?: string;
  exclude_rules?: string;
  priority: number;
  enabled: boolean;
}

export interface TopicCreate {
  name: string;
  description?: string;
  include_rules?: string;
  exclude_rules?: string;
  priority?: number;
  enabled?: boolean;
}

export interface TopicUpdate {
  name?: string;
  description?: string;
  include_rules?: string;
  exclude_rules?: string;
  priority?: number;
  enabled?: boolean;
}

export interface Endpoint {
  id: number;
  connector_type: EndpointConnectorType;
  name: string;
  target: string;
  enabled: boolean;
  weight: number;
  notes?: string;
}

export interface EndpointCreate {
  connector_type: EndpointConnectorType;
  name: string;
  target: string;
  enabled?: boolean;
  weight?: number;
  notes?: string;
}

export interface EndpointUpdate {
  connector_type?: EndpointConnectorType;
  name?: string;
  target?: string;
  enabled?: boolean;
  weight?: number;
  notes?: string;
}

export interface ConnectorQuery {
  id: number;
  connector_type: ConnectorType;
  query: string;
  topic_id?: number;
  topic_name?: string;
}

export type RunType = "ingest" | "ai" | "build_brief";
export type RunStatus = "running" | "success" | "failed";

export interface TavilyRunOptions {
  enabled?: boolean;
  search_depth?: "basic" | "advanced" | "fast" | "ultra-fast";
  max_results?: number;
  topic?: "general" | "news" | "finance";
  time_range?: "none" | "day" | "week" | "month" | "year" | "d" | "w" | "m" | "y";
  start_date?: string;
  end_date?: string;
  include_raw_content?: boolean;
  include_answer?: boolean;
  fetch_window_hours?: number;
}

export interface RunIngestionOptions {
  rss_max_items?: number;
  youtube_max_items?: number;
  twitter_max_items?: number;
  tavily?: TavilyRunOptions;
}

export interface RunAiOptions {
  timeout_seconds?: number;
}

export interface RunBriefOptions {
  max_items?: number;
  max_per_topic?: number;
  lookback_hours?: number;
}

export interface AppSettings {
  ingestion: {
    rss_max_items: number;
    youtube_max_items: number;
    twitter_max_items: number;
  };
  tavily: {
    search_depth: "basic" | "advanced" | "fast" | "ultra-fast";
    max_results: number;
    topic: "general" | "news" | "finance";
    time_range: "none" | "day" | "week" | "month" | "year";
    include_raw_content: boolean;
  };
  ai: {
    timeout_seconds: number;
    classification_timeout_seconds: number;
    extraction_timeout_seconds: number;
  };
  brief: {
    max_items: number;
    max_per_topic: number;
    lookback_hours: number;
    topic_brief_timeout_seconds: number;
    topic_brief_batch_size: number;
  };
}

export interface Run {
  id: number;
  run_type: RunType;
  started_at: string;
  finished_at?: string;
  status: RunStatus;
  stats_json?: Record<string, any>;
  error_text?: string;
}
