// Server-side API client. The API key stays on the server; it's never sent to
// the browser. Called from React server components.

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${API_KEY}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export type MetricsSummary = {
  calls_total: number;
  calls_today: number;
  acceptance_rate: number;
  avg_rounds_when_accepted: number | null;
  avg_final_rate: string | null;
  outcomes: Record<string, number>;
  sentiment: Record<string, number>;
  calls_by_day: { date: string; count: number }[];
};

export type CallListItem = {
  id: number;
  mc_number: string | null;
  carrier_name: string | null;
  load_id: string | null;
  outcome: string | null;
  sentiment: string | null;
  final_rate: string | null;
  rounds_used: number | null;
  agreement_reached: boolean | null;
  created_at: string;
};

export type CallListResponse = {
  calls: CallListItem[];
  total: number;
};

export type OfferItem = {
  id: number;
  round_number: number;
  carrier_offer: string;
  agent_counter: string | null;
  decision: string;
  created_at: string;
};

export type CallDetail = {
  call: CallListItem;
  transcript: string | null;
  extracted_fields: Record<string, unknown> | null;
  offers: OfferItem[];
};

export function getMetricsSummary() {
  return apiGet<MetricsSummary>("/api/v1/metrics/summary");
}

export function getCalls(limit = 50, offset = 0) {
  return apiGet<CallListResponse>(`/api/v1/calls?limit=${limit}&offset=${offset}`);
}

export function getCallDetail(id: number) {
  return apiGet<CallDetail>(`/api/v1/calls/${id}`);
}
