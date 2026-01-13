import type { AppSettings } from "@/types";

const SETTINGS_STORAGE_KEY = "sigdig.settings";

export const DEFAULT_SETTINGS: AppSettings = {
  ingestion: {
    rss_max_items: 10,
    youtube_max_items: 2,
    twitter_max_items: 5,
  },
  tavily: {
    search_depth: "advanced",
    max_results: 20,
    topic: "news",
    time_range: "day",
    include_raw_content: true,
  },
  ai: {
    timeout_seconds: 900,
    classification_timeout_seconds: 60,
    extraction_timeout_seconds: 90,
  },
  brief: {
    max_items: 15,
    max_per_topic: 3,
    lookback_hours: 48,
    topic_brief_timeout_seconds: 60,
    topic_brief_batch_size: 10,
  },
};

export function normalizeSettings(stored: Partial<AppSettings> | null): AppSettings {
  if (!stored) {
    return DEFAULT_SETTINGS;
  }
  const merged: AppSettings = {
    ingestion: {
      ...DEFAULT_SETTINGS.ingestion,
      ...(stored.ingestion || {}),
    },
    tavily: {
      ...DEFAULT_SETTINGS.tavily,
      ...(stored.tavily || {}),
    },
    ai: {
      ...DEFAULT_SETTINGS.ai,
      ...(stored.ai || {}),
    },
    brief: {
      ...DEFAULT_SETTINGS.brief,
      ...(stored.brief || {}),
    },
  };
  if (
    !["basic", "advanced", "fast", "ultra-fast"].includes(merged.tavily.search_depth)
  ) {
    merged.tavily.search_depth = DEFAULT_SETTINGS.tavily.search_depth;
  }
  if (!["general", "news", "finance"].includes(merged.tavily.topic)) {
    merged.tavily.topic = DEFAULT_SETTINGS.tavily.topic;
  }
  if (!["none", "day", "week", "month", "year"].includes(merged.tavily.time_range)) {
    merged.tavily.time_range = DEFAULT_SETTINGS.tavily.time_range;
  }
  if (!Number.isFinite(merged.ingestion.rss_max_items)) {
    merged.ingestion.rss_max_items = DEFAULT_SETTINGS.ingestion.rss_max_items;
  }
  if (!Number.isFinite(merged.ingestion.youtube_max_items)) {
    merged.ingestion.youtube_max_items = DEFAULT_SETTINGS.ingestion.youtube_max_items;
  }
  if (!Number.isFinite(merged.ingestion.twitter_max_items)) {
    merged.ingestion.twitter_max_items = DEFAULT_SETTINGS.ingestion.twitter_max_items;
  }
  if (!Number.isFinite(merged.ai.timeout_seconds)) {
    merged.ai.timeout_seconds = DEFAULT_SETTINGS.ai.timeout_seconds;
  }
  if (!Number.isFinite(merged.ai.classification_timeout_seconds)) {
    merged.ai.classification_timeout_seconds =
      DEFAULT_SETTINGS.ai.classification_timeout_seconds;
  }
  if (!Number.isFinite(merged.ai.extraction_timeout_seconds)) {
    merged.ai.extraction_timeout_seconds =
      DEFAULT_SETTINGS.ai.extraction_timeout_seconds;
  }
  if (!Number.isFinite(merged.brief.max_items)) {
    merged.brief.max_items = DEFAULT_SETTINGS.brief.max_items;
  }
  if (!Number.isFinite(merged.brief.max_per_topic)) {
    merged.brief.max_per_topic = DEFAULT_SETTINGS.brief.max_per_topic;
  }
  if (!Number.isFinite(merged.brief.lookback_hours)) {
    merged.brief.lookback_hours = DEFAULT_SETTINGS.brief.lookback_hours;
  }
  if (!Number.isFinite(merged.brief.topic_brief_timeout_seconds)) {
    merged.brief.topic_brief_timeout_seconds = DEFAULT_SETTINGS.brief.topic_brief_timeout_seconds;
  }
  if (!Number.isFinite(merged.brief.topic_brief_batch_size)) {
    merged.brief.topic_brief_batch_size = DEFAULT_SETTINGS.brief.topic_brief_batch_size;
  } else if (
    merged.brief.topic_brief_batch_size < 5
    || merged.brief.topic_brief_batch_size > 50
  ) {
    merged.brief.topic_brief_batch_size = DEFAULT_SETTINGS.brief.topic_brief_batch_size;
  }
  if (typeof merged.tavily.include_raw_content !== "boolean") {
    merged.tavily.include_raw_content = DEFAULT_SETTINGS.tavily.include_raw_content;
  }
  return merged;
}

export function loadSettings(): AppSettings {
  if (typeof window === "undefined") {
    return DEFAULT_SETTINGS;
  }
  const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
  if (!raw) {
    return DEFAULT_SETTINGS;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return normalizeSettings(parsed);
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: AppSettings) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
}
