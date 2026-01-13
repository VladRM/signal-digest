/**
 * API client for Signal Digest backend
 */

import type {
  Topic,
  TopicCreate,
  TopicUpdate,
  Endpoint,
  EndpointCreate,
  EndpointUpdate,
  EndpointConnectorType,
  Run,
  RunIngestionOptions,
  RunAiOptions,
  RunBriefOptions,
  AppSettings,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let detail = "";
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (payload) {
        detail = JSON.stringify(payload);
      }
    } catch {
      detail = "";
    }
    throw new ApiError(
      response.status,
      detail
        ? `API error: ${response.status} ${response.statusText} - ${detail}`
        : `API error: ${response.status} ${response.statusText}`
    );
  }

  return response.json();
}

// Topics API
export const topicsApi = {
  list: () => fetchApi<Topic[]>("/topics"),
  get: (id: number) => fetchApi<Topic>(`/topics/${id}`),
  create: (data: TopicCreate) =>
    fetchApi<Topic>("/topics", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: number, data: TopicUpdate) =>
    fetchApi<Topic>(`/topics/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    fetchApi<{ message: string }>(`/topics/${id}`, {
      method: "DELETE",
    }),
};

// Endpoints API
export const endpointsApi = {
  list: (connectorType?: EndpointConnectorType) => {
    const params = connectorType ? `?connector_type=${connectorType}` : "";
    return fetchApi<Endpoint[]>(`/endpoints${params}`);
  },
  get: (id: number) => fetchApi<Endpoint>(`/endpoints/${id}`),
  create: (data: EndpointCreate) =>
    fetchApi<Endpoint>("/endpoints", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: number, data: EndpointUpdate) =>
    fetchApi<Endpoint>(`/endpoints/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    fetchApi<{ message: string }>(`/endpoints/${id}`, {
      method: "DELETE",
    }),
};

// Runs API
export const runsApi = {
  list: (limit?: number) => {
    const params = limit ? `?limit=${limit}` : "";
    return fetchApi<Run[]>(`/run${params}`);
  },
  get: (id: number) => fetchApi<Run>(`/run/${id}`),
  cancel: (id: number) =>
    fetchApi<Run>(`/run/${id}/cancel`, {
      method: "POST",
    }),
  triggerIngestion: (options?: RunIngestionOptions) =>
    fetchApi<Run>("/run/ingest", {
      method: "POST",
      ...(options ? { body: JSON.stringify(options) } : {}),
    }),
  triggerAI: (options?: RunAiOptions) =>
    fetchApi<Run>("/run/ai", {
      method: "POST",
      ...(options ? { body: JSON.stringify(options) } : {}),
    }),
  buildBrief: (params?: { date?: string; mode?: string; options?: RunBriefOptions }) => {
    const query = new URLSearchParams();
    if (params?.date) query.append("date", params.date);
    query.append("mode", params?.mode ?? "morning");
    return fetchApi<Run>(`/run/build-brief?${query}`, {
      method: "POST",
      ...(params?.options ? { body: JSON.stringify(params.options) } : {}),
    });
  },
};

// Settings API
export const settingsApi = {
  get: () => fetchApi<AppSettings>("/settings"),
  update: (settings: AppSettings) =>
    fetchApi<AppSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),
};

// Briefs API
export const briefsApi = {
  get: (date?: string, mode: string = "morning") => {
    const params = new URLSearchParams();
    if (date) params.append("date", date);
    params.append("mode", mode);
    return fetchApi<any>(`/brief?${params}`);
  },
};

// Explore API
export const exploreApi = {
  list: (filters: { topic_id?: number; from_date?: string; to_date?: string; limit?: number; offset?: number } = {}) => {
    const params = new URLSearchParams();
    if (filters.topic_id) params.append("topic_id", filters.topic_id.toString());
    if (filters.from_date) params.append("from_date", filters.from_date);
    if (filters.to_date) params.append("to_date", filters.to_date);
    if (filters.limit) params.append("limit", filters.limit.toString());
    if (filters.offset) params.append("offset", filters.offset.toString());
    return fetchApi<any[]>(`/explore?${params}`);
  },
};
